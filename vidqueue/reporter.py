from dataclasses import dataclass
from datetime import datetime, timedelta
from math import log10
from pathlib import Path
from textwrap import dedent
from typing import Literal

from config import CONFIG  # TODO: fix import path

LOG_ANALYZE_PATH = Path(CONFIG["paths"]["log_analyze_path"])

SCAN_MODE = Literal["fast", "deep"]
RECORD_STATUS = Literal["OK", "SKIPPED", "FAILED"]

METRIC_BY_MODE = {
    "fast": "SSIM",
    "deep": "VMAF",
}


@dataclass(frozen=True)
class AnalysisRecord:
    paths: tuple[Path, Path]
    durations: tuple[float, float]
    mode: SCAN_MODE
    status: RECORD_STATUS
    score: float | str | None = None
    reduction: float | None = None
    sizes: tuple[int, int] | None = None
    note: str = ""


def _format_bytes(size: int) -> str:

    if size < 0:
        raise ValueError(f"Size cannot be negative: {size}")

    if size == 0:
        return "0 B"

    units = ["B", "kB", "MB", "GB", "TB"]
    index = min(int(log10(size) // 3), len(units) - 1)

    value = round(size / 1000 ** index, 2)
    formatted = f"{value}".removesuffix(".0")

    return f"{formatted} {units[index]}"


def _format_duration(seconds: float):
    time_str = str(timedelta(seconds=round(seconds, 3)))
    head, dot, tail = time_str.partition(".")

    return f"{head}.{tail[:3]}" if dot else head


def _build_report_path(
        stem: str,
        timestamp: datetime,
        extension: str = 'log',
        log_dir_path: Path = LOG_ANALYZE_PATH
) -> Path:

    formatted_time = timestamp.strftime('%Y-%m-%d_%H-%M-%S')
    file_name = f"{formatted_time}_{stem}.{extension}"
    return log_dir_path / file_name


def _build_single_report(record: AnalysisRecord) -> str:
    org_path, conv_path = record.paths
    dur_org = _format_duration(record.durations[0])
    dur_conv = _format_duration(record.durations[1])
    size_before, size_after = record.sizes or (0, 0)
    saved_bytes = size_before - size_after
    reduction = record.reduction or 0.0

    return dedent(f"""\
        File:     {org_path} -> {conv_path}
        Mode:     {record.mode}
        Duration: {dur_org} | {dur_conv}
        Quality:  {record.score}%
        Size:     {_format_bytes(size_before)} -> {_format_bytes(size_after)}
            Saved: {_format_bytes(saved_bytes)} - {reduction}%
    """)

