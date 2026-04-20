#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
LOTTIE_PLAYER = ROOT_DIR / "node_modules" / "lottie-web" / "build" / "player" / "lottie.min.js"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render first frame of a .tgs animation to PNG.")
    parser.add_argument("input", help="Input .tgs file")
    parser.add_argument("output", help="Output .png file")
    parser.add_argument("--size", type=int, default=384, help="Canvas size in pixels")
    return parser.parse_args()


def load_tgs_json(file_path: Path) -> dict:
    with gzip.open(file_path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def build_capture_html(animation_data: dict, size: int) -> str:
    payload = json.dumps(animation_data, ensure_ascii=False)
    player_url = LOTTIE_PLAYER.resolve().as_uri()
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <style>
    html, body {{
      margin: 0;
      width: {size}px;
      height: {size}px;
      overflow: hidden;
      background: transparent;
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
    const target = document.getElementById('app');
    const firstFrame = Number(animationData.ip || 0);
    const animation = lottie.loadAnimation({{
      container: target,
      renderer: 'svg',
      loop: false,
      autoplay: false,
      animationData,
      rendererSettings: {{ preserveAspectRatio: 'xMidYMid meet' }},
    }});

    animation.addEventListener('DOMLoaded', () => {{
      animation.goToAndStop(firstFrame, true);
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


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    animation_data = load_tgs_json(input_path)

    with tempfile.TemporaryDirectory(prefix="tgs-still-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        html_path = temp_dir / "capture.html"
        html_path.write_text(build_capture_html(animation_data, args.size), encoding="utf-8")

        run_command([
            "google-chrome",
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
            "--allow-file-access-from-files",
            "--default-background-color=00000000",
            f"--window-size={args.size},{args.size}",
            f"--screenshot={output_path}",
            html_path.resolve().as_uri(),
        ])


if __name__ == "__main__":
    main()
