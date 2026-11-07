from datetime import datetime
from pathlib import Path

from ..config import CONFIG
from ..utils import SUFFIX_FORMATS
from ..video_analyzer import analyze


def _get_videos(path_dir: Path) -> dict[str, Path]:

    return {
        p.stem: p for p in path_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIX_FORMATS
    }


def get_matched_pairs(original_dir: Path, converted_dir: Path) -> dict[str, tuple[Path, Path]]:

    orig_vids = _get_videos(original_dir)
    conv_vids = _get_videos(converted_dir)

    common_stems = orig_vids.keys() & conv_vids.keys()

    return {
        stem: (orig_vids[stem], conv_vids[stem])
        for stem in sorted(common_stems)
    }

def calculate_size_reduction(original_video: Path, converted_video: Path):

    orig_vids = original_video.stat().st_size
    conv_vids = converted_video.stat().st_size

    if orig_vids == 0.0:
        return 0.0

    reduction = (1.0 - (conv_vids/orig_vids)) * 100
    return round(reduction, 2)

def analyze_queue(original_dir: Path, converted_dir: Path, mode_type: str):

    vids_pairs = get_matched_pairs(original_dir, converted_dir)

    for name, (orig_file, conv_file) in vids_pairs.items():
        print(name)
        for step in analyze(orig_file, conv_file, mode_type):
            print(step)
