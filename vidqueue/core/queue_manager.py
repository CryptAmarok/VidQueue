from pathlib import Path
import json


STATE_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = STATE_DIR / ".queue_state.json"
TMP_FILE = STATE_DIR / ".queue_state.tmp"


def save_queue_state(video_paths: list[Path], args: list) -> None:
    """Save current queue state to a JSON file"""
    if not video_paths:
        return

    arguments = args.copy()

    queue = video_paths[::-1]
    input_index = arguments.index('-i')
    del arguments[input_index + 1]
    output_file_path = Path(arguments.pop())
    output_path = output_file_path.parent
    data = {
        'videos_list': [str(path) for path in queue],
        'output_path': str(output_path),
        'ffmpeg_settings': arguments,
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
        None


def is_empty() -> bool:

    # if the file doesn't exist
    if not STATE_FILE.exists():
        return True

    with STATE_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            video_list = data.get('video_list', [])
            return video_list == 0

        except:
            # file is corrupted
            return True
