from pathlib import Path

from ..utils import SUFFIX_FORMATS
from ..video_analyzer import analyze


def get_videos(path_dir: Path) -> dict[str, Path]:

    return {
        p.stem: p for p in path_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIX_FORMATS
    }

def analyze_queue(original_dir: Path, converted_dir: Path, mode_type: str):
    pass