from pathlib import Path
import json

STATE_DIR = Path(__file__).parents[2]
STATE_FILE = STATE_DIR / ".queue_state.json"
TMP_FILE = STATE_DIR / ".queue_state.tmp"


def save_queue_state(video_paths: list[Path], output_path: Path) -> None:
    """Save current queue state to a JSON file"""
    if not video_paths:
        return

    queue = video_paths[::-1]
    data = {
        'videos_list': [str(path) for path in queue],
        'output_path': str(output_path)
    }

    with TMP_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f)

    TMP_FILE.replace(STATE_FILE)


def get_next_video():
    pass


def is_empty():
    pass
