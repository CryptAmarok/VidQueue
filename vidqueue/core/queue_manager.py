import json
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parents[2]
STATE_FILE = STATE_DIR / ".queue_state.json"
TMP_FILE = STATE_DIR / ".queue_state.tmp"


def save_queue_state(video_paths: list[Path], output_path: Path,
                     ffmpeg_settings: list, sample_width: int | str) -> None:
    """Save the current queue state to a JSON file."""
    if not video_paths:
        return

    if '-i' not in ffmpeg_settings:
        raise ValueError("'-i' not found in ffmpeg settings")

    ffmpeg_args = ffmpeg_settings.copy()

    # Find the input video position in the ffmpeg command
    input_index = ffmpeg_args.index('-i') + 1
    ffmpeg_args[input_index] = '__INPUT__'
    ffmpeg_args[-1] = '__OUTPUT__'

    ffmpeg_args = [
        str(arg).replace(str(sample_width), '__WIDTH__')
        for arg in ffmpeg_args
    ]

    data = {
        'videos_list': [str(path) for path in video_paths[::-1]],
        'output_path': str(output_path),
        'ffmpeg_settings': ffmpeg_args,
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


def is_empty() -> bool:

    # if the file doesn't exist
    if not STATE_FILE.exists():
        return True

    with STATE_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            video_list = data.get('videos_list', [])
            return len(video_list) == 0

        except:
            # file is corrupted
            return True


def clear_queue() -> None:
    with STATE_FILE.open("r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
            return
    video_list = data.get('videos_list', [])
    if len(video_list) == 0:
        STATE_FILE.unlink()
