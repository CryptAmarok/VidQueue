from pathlib import Path

from ..utils import SUFFIX_FORMATS
from .ffmpeg_runner import get_video_length


def _get_videos(path_dir: Path) -> dict[str, Path]:
    return {
        p.stem: p for p in path_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUFFIX_FORMATS
    }


def get_matched_pairs(
    original_dir: Path,
    converted_dir: Path
) -> dict[str, tuple[Path, Path]]:
    """Pairs videos from two directories by matching stems."""
    orig_vids = _get_videos(original_dir)
    conv_vids = _get_videos(converted_dir)

    common_stems = orig_vids.keys() & conv_vids.keys()

    return {
        stem: (orig_vids[stem], conv_vids[stem])
        for stem in sorted(common_stems)
    }


def calculate_size_reduction(
    original_video: Path,
    converted_video: Path
) -> float:
    """Calculates the percentage reduction in file size."""
    orig_vid = original_video.stat().st_size
    conv_vid = converted_video.stat().st_size

    if orig_vid == 0:
        return 0

    reduction = (1.0 - (conv_vid/orig_vid)) * 100
    return round(reduction, 2)


def is_duration_mismatched(
    original_video: Path,
    converted_video: Path,
    tolerance: float = 0.5
) -> bool:
    """Checks if absolute duration difference between videos 
    exceeds tolerance."""

    t_orig_vid = get_video_length(original_video)
    t_conv_vid = get_video_length(converted_video)

    # Absolute Duration Difference
    delta_t = abs(t_orig_vid - t_conv_vid)

    return delta_t > tolerance
