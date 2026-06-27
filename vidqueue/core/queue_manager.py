import json
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = STATE_DIR / ".queue_state.json"
TMP_FILE = STATE_DIR / ".queue_state.tmp"


def save_queue_state(video_paths: list[Path], output_path: Path,
                     ffmpeg_args: dict, extra: dict) -> None:
    """Save the current queue state to a JSON file."""

    data = {
        'videos_list': [str(path) for path in video_paths[::-1]],
        'output_path': str(output_path),
        'ffmpeg_settings': {
            'codec': ffmpeg_args.get("codec"),
            'gpu': ffmpeg_args.get("gpu"),
            'kwargs': extra
        }
    }

    with TMP_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)

    TMP_FILE.replace(STATE_FILE)


def load_queue() -> dict | None:

    with STATE_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return None

    videos_list = [Path(p) for p in data.get('videos_list', [])]
    output_path = data.get('output_path', None)
    ffmpeg_settings = data.get('ffmpeg_settings', None)

    if videos_list and output_path and ffmpeg_settings:
        return {
            'videos_list': videos_list,
            'output_path': output_path,
            'ffmpeg_settings': ffmpeg_settings
        }
    else:
        return None


def clear_queue() -> None:
    with STATE_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return
    video_list = data.get('videos_list', [])
    if len(video_list) == 0:
        STATE_FILE.unlink()
