from pathlib import Path

from ..utils import SUFFIX_FORMATS
from ..video_analyzer import analyze


def get_videos(path_dir: Path) -> dict[str, Path]:

    return {
        p.stem: p for p in path_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIX_FORMATS
    }


def analyze_queue(original_dir: Path, converted_dir: Path, mode_type: str):

    original_videos = get_videos(original_dir)
    converted_videos = get_videos(converted_dir)

    orig_stems = original_videos.keys()
    conv_stems = converted_videos.keys()

    common_stems = orig_stems & conv_stems

    for video_name in common_stems:
        orig_file = original_videos[video_name]
        conv_file = converted_videos[video_name]
        for step in analyze(orig_file, conv_file, mode_type):
            print(step)
