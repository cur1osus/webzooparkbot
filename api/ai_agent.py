#!/usr/bin/env python3
"""
ZooPark AI Enemy Agent
======================
Автономный ИИ-игрок. Использует qwen + ZooPark MCP-сервер:
qwen сам вызывает инструменты (get_game_state, buy_animal, create_mp_game...)
и строит цепочки действий без дополнительного кода.

Требования:
  - qwen mcp add zoopark <python> api/mcp_server.py   (уже настроено)
  - ZOOPARK_SESSION в ~/.qwen/settings.json → mcpServers.zoopark.env  (уже настроено)

Запуск:
  python api/ai_agent.py

Параметры (env):
  ZOOPARK_AI_NAME       — имя агента в логах              (default: ИИван)
  ZOOPARK_AI_IDLE       — секунд между ходами            (default: 90)
  ZOOPARK_AI_TIMEOUT    — timeout одного вызова qwen     (default: 6000)
  ZOOPARK_AI_LOCK_ID    — идентификатор lock-файла       (default: ZOOPARK_AI_NAME)
"""

import asyncio
import fcntl
import hashlib
import json
import logging
import logging.handlers
import os
import re
import signal
import subprocess
import time

# ─── Config ───────────────────────────────────────────────────────────────────

AI_NAME = os.getenv("ZOOPARK_AI_NAME", "ИИван")
LOOP_IDLE = int(os.getenv("ZOOPARK_AI_IDLE", "90"))
QWEN_TIMEOUT = int(os.getenv("ZOOPARK_AI_TIMEOUT", "600"))
LLM_CMD = os.getenv("ZOOPARK_AI_CMD", "qwen")
LOCK_ID = os.getenv("ZOOPARK_AI_LOCK_ID", AI_NAME)
ZOOPARK_SESSION = os.getenv("ZOOPARK_SESSION", "")
ZOOPARK_API_URL = os.getenv("ZOOPARK_API_URL", "https://89-22-224-52.sslip.io:8443")


def _lock_file_path(lock_id: str) -> str:
    safe_prefix = re.sub(r"[^a-zA-Z0-9_.-]+", "_", lock_id).strip("._-")[:24] or "agent"
    suffix = hashlib.sha1(lock_id.encode("utf-8")).hexdigest()[:12]
    return f"/tmp/zoopark_ai_{safe_prefix}_{suffix}.lock"


LOCK_FILE = _lock_file_path(LOCK_ID)

LOG_FILE = os.getenv("ZOOPARK_AI_LOG", f"/tmp/zoopark_ai_{re.sub(r'[^a-zA-Z0-9_.-]+', '_', LOCK_ID)}.log")

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_file.setFormatter(_fmt)

logging.basicConfig(level=logging.DEBUG, handlers=[_console, _file])
log = logging.getLogger(AI_NAME)
log.setLevel(logging.DEBUG)

BACKOFF_RULES = [
    (
        [
            "Qwen API quota exceeded",
            "Free allocated quota exceeded",
            "free daily quota has been reached",
        ],
        3600,
        "Квота qwen исчерпана (~1000/день). Жду 1ч.",
    ),
    (
        [
            "Connection error",
            "API Error:",
        ],
        120,
        "Ошибка соединения qwen. Жду 2 мин.",
    ),
    (
        [
            "rate_limit_exceeded",
            "Rate limit reached",
            "RateLimitError",
        ],
        60,
        "Лимит запросов codex. Жду 1 мин.",
    ),
    (
        [
            "insufficient_quota",
            "You exceeded your current quota",
        ],
        3600,
        "Квота OpenAI исчерпана. Жду 1ч.",
    ),
]

LOCK_HANDLE = None


# ─── Уведомление владельца ────────────────────────────────────────────────────

def _notify_owner(summary: str, wait_sec: int) -> None:
    """Отправить сводку хода в Telegram через /api/agent/notify."""
    if not ZOOPARK_SESSION:
        return
    import urllib.request as _req
    import urllib.error

    lines = [summary]
    if wait_sec >= 3600:
        next_str = f"{wait_sec // 3600}ч"
    elif wait_sec >= 60:
        next_str = f"{wait_sec // 60}м"
    else:
        next_str = f"{wait_sec}с"
    lines.append(f"\n⏱ Следующий ход через {next_str}")

    payload = json.dumps(
        {"text": "\n".join(lines), "agent_name": AI_NAME},
        ensure_ascii=False,
    ).encode()
    try:
        _req.urlopen(
            _req.Request(
                f"{ZOOPARK_API_URL}/api/agent/notify",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Web-Session": ZOOPARK_SESSION,
                },
                method="POST",
            ),
            timeout=10,
        )
    except urllib.error.HTTPError as exc:
        log.warning("notify: HTTP %s", exc.code)
    except Exception as exc:
        log.warning("notify: %s", exc)


# ─── Системный промпт ─────────────────────────────────────────────────────────

SYSTEM = f"""Ты — {AI_NAME}, автономный ИИ-игрок в ZooPark. Цель: топ-10 по доходу в минуту.
Используй все доступные инструменты ZooPark чтобы развивать зоопарк, участвовать в играх и управлять экономикой.
Ты можешь свободно исследовать состояние игры, перечитывать память, сравнивать варианты и строить цепочки действий через инструменты MCP.
Не ограничивайся одним запросом к состоянию: если для хорошего решения нужно больше данных, собирай их.
В конце дай краткий итог хода и укажи рекомендуемую паузу до следующего хода — учитывай сколько времени нужно накопить ресурсы для следующего действия.
Предпочтительный формат финала:
{{"summary": "кратко что сделал", "seconds": 90}}
Но если удобнее, можешь ответить обычным текстом и отдельной строкой `seconds: N`.

ВАЖНО: НЕ используй shell-команды (sleep, bash, sh и т.п.). Если нужно подождать банковский тик или накопить ресурсы — завершай ход и укажи нужную паузу в поле seconds. Следующий ход запустится автоматически."""

# ─── Вызов qwen ───────────────────────────────────────────────────────────────

TASK = "Сделай полноценный ход в ZooPark: исследуй состояние, при необходимости собери дополнительные данные через MCP-инструменты, прими решения, выполни действия и в конце кратко подведи итог хода с рекомендуемой паузой до следующего хода."


def _clamp_wait(wait_sec: int) -> int:
    return max(60, min(600, wait_sec))


def _shorten(text: str, limit: int = 300) -> str:
    return text.strip().replace("\n", " ")[:limit]


def _detect_backoff(*chunks: str) -> int | None:
    combined = "\n".join(chunk for chunk in chunks if chunk)
    if not combined:
        return None

    for markers, wait_sec, message in BACKOFF_RULES:
        if any(marker.lower() in combined.lower() for marker in markers):
            log.warning("⚠️  %s", message)
            return wait_sec

    return None


def _load_qwen_events(raw: str) -> list[dict]:
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    raise ValueError(f"неожиданный JSON-тип: {type(parsed).__name__}")


def _iter_json_object_candidates(text: str):
    if not text:
        return

    for fenced in re.findall(
        r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE
    ):
        yield fenced

    depth = 0
    start = None
    in_string = False
    escaped = False

    for idx, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "{":
            if depth == 0:
                start = idx
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start : idx + 1]
                start = None


def _parse_summary_payload(text: str) -> tuple[str, int]:
    wait_sec = LOOP_IDLE
    summary = text.strip()

    candidates = [text.strip(), *_iter_json_object_candidates(text)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        raw_summary = payload.get("summary")
        raw_seconds = payload.get("seconds")

        if isinstance(raw_summary, str) and raw_summary.strip():
            summary = raw_summary.strip()

        try:
            wait_sec = _clamp_wait(int(raw_seconds))
        except (TypeError, ValueError):
            wait_sec = LOOP_IDLE

        return summary, wait_sec

    match = re.search(r"seconds[:\s]+(\d+)", text, re.IGNORECASE)
    if match:
        wait_sec = _clamp_wait(int(match.group(1)))

    cleaned = re.sub(r"```(?:json)?|```", "", summary, flags=re.IGNORECASE).strip()
    cleaned = re.sub(
        r"\n?seconds[:\s]+\d+\s*$", "", cleaned, flags=re.IGNORECASE
    ).strip()
    return cleaned, wait_sec


def _extract_summary_text(events: list[dict]) -> str:
    for event in reversed(events):
        if event.get("type") == "result":
            result_text = event.get("result", "")
            if isinstance(result_text, str):
                return result_text

    for event in reversed(events):
        if event.get("type") != "assistant":
            continue
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                value = block.get("text")
                if isinstance(value, str) and value.strip():
                    texts.append(value.strip())
        if texts:
            return "\n".join(texts)

    return ""


def _get_content_blocks(event: dict) -> list:
    """Возвращает content-блоки из assistant-события (оба формата: с message и без)."""
    # формат с MCP: event["message"]["content"]
    message = event.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, list):
            return content
    # формат без MCP: event["content"]
    content = event.get("content")
    if isinstance(content, list):
        return content
    return []


def _log_thinking(events: list[dict]) -> None:
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in _get_content_blocks(event):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "thinking":
                text = (block.get("thinking") or "").strip()
                if text:
                    log.debug("💭 %s", text)
            elif block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    log.info("💬 %s", text)


def _log_tool_calls(events: list[dict]) -> None:
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in _get_content_blocks(event):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name", "tool"))
            tool_name = name.replace("mcp__zoopark__", "")
            tool_input = (
                block.get("input") if isinstance(block.get("input"), dict) else {}
            )
            log.info("→ %s %s", tool_name, tool_input)


def _terminate_process_group(proc: subprocess.Popen, sig: int) -> None:
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass


def run_codex() -> tuple[str, int]:
    """
    Запустить codex exec с ZooPark MCP. Вернуть (итог, секунд_ожидания).
    Codex выводит JSONL-поток событий; MCP-инструменты подключены через config.toml.
    """
    full_prompt = f"{SYSTEM}\n\n{TASK}"
    cmd = [
        "codex", "exec",
        "--json",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--ephemeral",
        full_prompt,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        log.error("codex не найден")
        return "", LOOP_IDLE

    try:
        stdout, stderr = proc.communicate(timeout=QWEN_TIMEOUT)
    except subprocess.TimeoutExpired:
        log.error("codex timeout (>%ss), завершаю process group", QWEN_TIMEOUT)
        _terminate_process_group(proc, signal.SIGTERM)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc, signal.SIGKILL)
            proc.communicate()
        return "", LOOP_IDLE
    except KeyboardInterrupt:
        _terminate_process_group(proc, signal.SIGTERM)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc, signal.SIGKILL)
            proc.communicate()
        raise

    backoff_wait = _detect_backoff(stdout, stderr)
    if backoff_wait is not None:
        return "", backoff_wait

    if proc.returncode != 0:
        details = _shorten(stderr or stdout)
        log.error("codex завершился с кодом %s: %s", proc.returncode, details)
        return "", LOOP_IDLE

    # Парсим JSONL: каждая строка — отдельный JSON-объект
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if not events:
        log.warning("codex вернул пустой ответ: %s", _shorten(stderr, 200))
        return "", LOOP_IDLE

    _log_codex_events(events)

    summary_text = _extract_codex_summary(events)
    if not summary_text:
        log.warning("codex не вернул итоговое сообщение")
        return "", LOOP_IDLE

    summary, wait_sec = _parse_summary_payload(summary_text)
    return summary, wait_sec


def _log_codex_events(events: list[dict]) -> None:
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        item_type = item.get("type", "")
        if item_type == "agent_message":
            text = (item.get("text") or "").strip()
            if text:
                log.info("💬 %s", text)
        elif item_type in ("mcp_call", "mcp_tool_call"):
            name = str(item.get("name") or item.get("tool") or "tool").replace("mcp__zoopark__", "")
            inp = item.get("input") or item.get("arguments") or {}
            if isinstance(inp, str):
                try:
                    inp = json.loads(inp)
                except Exception:
                    pass
            log.info("→ %s %s", name, inp)
        elif item_type == "command_execution":
            cmd_text = item.get("command", "")
            exit_code = item.get("exit_code")
            log.debug("$ %s (exit=%s)", _shorten(cmd_text, 100), exit_code)
        elif item_type not in ("agent_turn_start",):
            log.debug("[%s] %s", item_type, _shorten(str(item), 120))


def _extract_codex_summary(events: list[dict]) -> str:
    # Берём текст последнего agent_message
    for event in reversed(events):
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            text = item.get("text", "")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return ""


def run_qwen() -> tuple[str, int]:
    """
    Запустить qwen с ZooPark MCP. Вернуть (итог, секунд_ожидания).
    qwen сам вызывает инструменты через MCP и возвращает результат.
    """
    cmd = [LLM_CMD, "-o", "json", "--system-prompt", SYSTEM, TASK]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        log.error("qwen не найден")
        return "", LOOP_IDLE

    try:
        stdout, stderr = proc.communicate(timeout=QWEN_TIMEOUT)
    except subprocess.TimeoutExpired:
        log.error("qwen timeout (>%ss), завершаю process group", QWEN_TIMEOUT)
        _terminate_process_group(proc, signal.SIGTERM)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc, signal.SIGKILL)
            proc.communicate()
        return "", LOOP_IDLE
    except KeyboardInterrupt:
        _terminate_process_group(proc, signal.SIGTERM)
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            _terminate_process_group(proc, signal.SIGKILL)
            proc.communicate()
        raise

    raw = stdout.strip()
    backoff_wait = _detect_backoff(raw, stderr)
    if backoff_wait is not None:
        return "", backoff_wait

    if proc.returncode != 0:
        details = _shorten(stderr or raw)
        log.error("qwen завершился с кодом %s: %s", proc.returncode, details)
        return "", LOOP_IDLE

    if not raw:
        log.warning("qwen вернул пустой ответ: %s", _shorten(stderr, 200))
        return "", LOOP_IDLE

    try:
        events = _load_qwen_events(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        log.error("Не удалось разобрать ответ qwen: %s; stdout=%s", exc, _shorten(raw))
        if stderr.strip():
            log.error("stderr qwen: %s", _shorten(stderr))
        return "", LOOP_IDLE

    _log_thinking(events)
    _log_tool_calls(events)

    summary_text = _extract_summary_text(events)
    if not summary_text:
        log.warning("qwen не вернул итоговый result")
        return "", LOOP_IDLE

    summary, wait_sec = _parse_summary_payload(summary_text)
    return summary, wait_sec


# ─── Основной цикл ────────────────────────────────────────────────────────────


async def run():
    log.info("=== %s запущен (llm: %s, idle: %ds, lock_id: %s) ===", AI_NAME, LLM_CMD, LOOP_IDLE, LOCK_ID)

    while True:
        t0 = time.monotonic()
        log.info("── Новый ход ──")

        try:
            if LLM_CMD == "codex":
                summary, wait_sec = run_codex()
            else:
                summary, wait_sec = run_qwen()
        except KeyboardInterrupt:
            log.info("Остановлен")
            break
        except Exception as exc:
            log.exception("Ошибка: %s", exc)
            summary = ""
            wait_sec = 30

        if summary:
            log.info("✓ %s", _shorten(summary))
            _notify_owner(summary, wait_sec)

        elapsed = time.monotonic() - t0
        sleep_for = max(5.0, wait_sec - elapsed)
        log.info("Следующий ход через %.0fс\n", sleep_for)
        await asyncio.sleep(sleep_for)


def _acquire_lock() -> None:
    global LOCK_HANDLE

    LOCK_HANDLE = open(LOCK_FILE, "w")
    try:
        fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        LOCK_HANDLE.close()
        LOCK_HANDLE = None
        log.error("Экземпляр с lock_id=%s уже запущен (%s)", LOCK_ID, LOCK_FILE)
        raise SystemExit(1)

    LOCK_HANDLE.seek(0)
    LOCK_HANDLE.write(str(os.getpid()))
    LOCK_HANDLE.truncate()
    LOCK_HANDLE.flush()


def _release_lock() -> None:
    global LOCK_HANDLE

    if LOCK_HANDLE is None:
        return

    try:
        fcntl.flock(LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass

    LOCK_HANDLE.close()
    LOCK_HANDLE = None


if __name__ == "__main__":
    _acquire_lock()
    try:
        asyncio.run(run())
    finally:
        _release_lock()
