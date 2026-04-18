#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import math
import subprocess
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
LOTTIE_PLAYER = (
    ROOT_DIR / "node_modules" / "lottie-web" / "build" / "player" / "lottie.min.js"
)
DEFAULT_INPUT_GLOB = ROOT_DIR / "downloads" / "media"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render downloaded .tgs files to animated GIF/WebP previews."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Specific .tgs files to render. Defaults to downloads/media/*.tgs.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=512,
        help="Preview width and height in pixels.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Output preview frame rate.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=90,
        help="Cap rendered frames to keep previews fast and small.",
    )
    parser.add_argument(
        "--background",
        default="#17212b",
        help="Background color for screenshots.",
    )
    return parser.parse_args()


def resolve_inputs(paths: list[str]) -> list[Path]:
    if paths:
        files = [Path(path).resolve() for path in paths]
    else:
        files = sorted(DEFAULT_INPUT_GLOB.glob("*.tgs"))

    return [path for path in files if path.is_file()]


def load_tgs_json(file_path: Path) -> dict:
    with gzip.open(file_path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def build_capture_html(animation_data: dict, size: int, background: str) -> str:
    payload = json.dumps(animation_data, ensure_ascii=False)
    player_url = LOTTIE_PLAYER.resolve().as_uri()
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>TGS Frame Capture</title>
  <style>
    html, body {{
      margin: 0;
      width: {size}px;
      height: {size}px;
      overflow: hidden;
      background: {background};
    }}
    #app {{
      width: {size}px;
      height: {size}px;
    }}
    svg {{
      width: 100% !important;
      height: 100% !important;
    }}
  </style>
</head>
<body>
  <div id=\"app\"></div>
  <script src=\"{player_url}\"></script>
  <script>
    const animationData = {payload};
    const params = new URLSearchParams(window.location.search);
    const frame = Number(params.get('frame') || '0');
    const target = document.getElementById('app');
    const animation = lottie.loadAnimation({{
      container: target,
      renderer: 'svg',
      loop: false,
      autoplay: false,
      animationData,
      rendererSettings: {{ preserveAspectRatio: 'xMidYMid meet' }},
    }});

    animation.addEventListener('DOMLoaded', () => {{
      animation.goToAndStop(frame, true);
      requestAnimationFrame(() => requestAnimationFrame(() => {{
        document.body.setAttribute('data-ready', '1');
      }}));
    }});
  </script>
</body>
</html>
"""


def run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def detect_frame_numbers(
    animation_data: dict, fps: int, max_frames: int
) -> tuple[list[int], int]:
    source_fps = float(animation_data.get("fr") or fps)
    start_frame = int(math.floor(animation_data.get("ip", 0)))
    end_frame = int(math.ceil(animation_data.get("op", start_frame + 1)))
    total_source_frames = max(1, end_frame - start_frame)
    duration_seconds = total_source_frames / source_fps
    target_frame_count = max(2, min(max_frames, int(math.ceil(duration_seconds * fps))))

    frame_numbers: list[int] = []
    for index in range(target_frame_count):
        if target_frame_count == 1:
            frame = start_frame
        else:
            progress = index / (target_frame_count - 1)
            frame = start_frame + round(progress * max(0, total_source_frames - 1))
        if not frame_numbers or frame != frame_numbers[-1]:
            frame_numbers.append(frame)

    return frame_numbers, fps


def capture_frames(
    file_path: Path,
    html_path: Path,
    frames_dir: Path,
    size: int,
    frame_numbers: list[int],
) -> None:
    base_url = html_path.resolve().as_uri()
    for index, frame in enumerate(frame_numbers):
        screenshot_path = frames_dir / f"frame_{index:04d}.png"
        url = f"{base_url}?frame={frame}"
        run_command(
            [
                "google-chrome",
                "--headless",
                "--no-sandbox",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--window-size={size},{size}",
                "--run-all-compositor-stages-before-draw",
                "--allow-file-access-from-files",
                "--virtual-time-budget=1500",
                f"--screenshot={screenshot_path}",
                url,
            ]
        )


def render_outputs(input_path: Path, frames_dir: Path, fps: int) -> tuple[Path, Path]:
    preview_dir = input_path.parent.parent / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    base_name = input_path.stem
    gif_path = preview_dir / f"{base_name}.gif"
    webp_path = preview_dir / f"{base_name}.webp"
    palette_path = frames_dir / "palette.png"

    run_command(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%04d.png"),
            "-vf",
            "palettegen=reserve_transparent=0",
            str(palette_path),
        ]
    )
    run_command(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%04d.png"),
            "-i",
            str(palette_path),
            "-lavfi",
            "paletteuse=dither=bayer:bayer_scale=5",
            str(gif_path),
        ]
    )
    run_command(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%04d.png"),
            "-loop",
            "0",
            "-c:v",
            "libwebp_anim",
            "-lossless",
            "1",
            str(webp_path),
        ]
    )

    return gif_path, webp_path


def render_preview(
    input_path: Path, size: int, fps: int, max_frames: int, background: str
) -> tuple[Path, Path]:
    animation_data = load_tgs_json(input_path)
    frame_numbers, effective_fps = detect_frame_numbers(animation_data, fps, max_frames)

    with tempfile.TemporaryDirectory(prefix="tgs-preview-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        html_path = temp_dir / "capture.html"
        frames_dir = temp_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            build_capture_html(animation_data, size=size, background=background),
            encoding="utf-8",
        )
        capture_frames(
            input_path, html_path, frames_dir, size=size, frame_numbers=frame_numbers
        )
        return render_outputs(input_path, frames_dir, effective_fps)


def main() -> int:
    args = parse_args()
    if not LOTTIE_PLAYER.is_file():
        raise SystemExit(f"lottie-web player not found: {LOTTIE_PLAYER}")

    inputs = resolve_inputs(args.inputs)
    if not inputs:
        raise SystemExit("No .tgs files found to render")

    for input_path in inputs:
        gif_path, webp_path = render_preview(
            input_path,
            size=args.size,
            fps=args.fps,
            max_frames=args.max_frames,
            background=args.background,
        )
        print(f"Rendered {input_path.name} -> {gif_path}")
        print(f"Rendered {input_path.name} -> {webp_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
