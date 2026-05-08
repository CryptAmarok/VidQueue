import re
import subprocess
import time
from pathlib import Path
from typing import Generator

from vidqueue.core.ffmpeg_runner import get_video_length, get_video_width


MODE_CONFIGS = {
    'fast': {
        'default_filter': "[0:v][1:v]ssim;[0:v][1:v]psnr",
        'regexes': {
            "ssim": re.compile(r"All:(\d+\.\d+)"),
            "psnr": re.compile(r"average:(\d+\.\d+)")
        }
    },
    'deep': {
        'default_filter': "[1:v][0:v]libvmaf",
        'regexes': {
            "vmaf": re.compile(r"score: (\d+\.\d+)")
        }
    }
}


def _metric_filters(mode: str) -> str:

    if mode == 'deep':
        return "[1:v][0:v]scale2ref[dist][ref];[dist][ref]libvmaf"
    elif mode == 'fast':
        step_scale = "[1:v][0:v]scale2ref[dist][ref]"
        step_split_dist = "[dist]split=2[dist1][dist2]"
        step_split_ref = "[ref]split=2[ref1][ref2]"
        step_ssim = "[dist1][ref1]ssim"
        step_psnr = "[dist2][ref2]psnr"
        return ';'.join(
            [step_scale, step_split_dist, step_split_ref,
             step_ssim, step_psnr]
        )
    raise ValueError(f"Invalid mode: '{mode}'.")


def analyze(
        file_path: Path,
        compressed_file_path: Path,
        mode: str = 'fast') -> Generator[
        dict[str, str | float | None], None, None]:
    """
    Analyzes the quality of a compressed video against the original
        using SSIM/PSNR (fast mode) or VMAF (deep mode) metrics.

    This function runs FFmpeg as a subprocess and acts as a generator,
    yielding real-time progress updates based on the processed video time.
    Upon completion, it calculates and yields a normalized overall quality
    score as a percentage based on the selected mode. It ensures safe and
    complete termination of the subprocess regardless of the execution flow.

    Note:
        The two files must be of the same resolution.

    Args:
        file_path (pathlib.Path): Path to the original (reference) video 
            file.
        compressed_file_path (pathlib.Path): Path to the compressed video 
            file.
        mode (str, optional): Analysis mode. 
            - 'fast': Uses SSIM and PSNR for quick calculation (default).
            - 'deep': Uses VMAF for more perceptually accurate quality 
                analysis.

    Yields:
        dict: A dictionary containing progress and final results. Keys 
            include:
            - 'percent' (float | None): Current progress percentage 
                (0.0 - 100.0).
            - 'final' (str | None): The final quality score 
                (e.g., '95.50%'), yielded only in the final iteration.
            - 'error' (str): (Optional) Error message if the subprocess 
                fails.

    Raises:
        ValueError: If either input file does not exist or if an invalid 
            mode is provided.
    """

    if not isinstance(mode, str):
        raise ValueError(f"Invalid mode type: {type(mode).__name__}.")

    mode = mode.lower().strip()

    if mode not in MODE_CONFIGS:
        raise ValueError(f"Invalid mode: '{mode}'. Expected 'fast' or 'deep'.")

    if not file_path.exists() or not compressed_file_path.exists():
        raise ValueError("Input file don't exists. Check paths")

    original_vid = get_video_width(file_path)
    convert_vid = get_video_width(compressed_file_path)

    is_resize = original_vid != convert_vid

    patterns = {}
    if is_resize:
        filters = _metric_filters(mode)
    else:
        filters = MODE_CONFIGS[mode]['default_filter']

    patterns = MODE_CONFIGS[mode]['regexes']

    ffmpeg_args = [
        'ffmpeg',
        '-i', str(file_path),
        '-i', str(compressed_file_path),
        '-lavfi', filters,
        '-f', 'null',
        '-'
    ]

    process = subprocess.Popen(
        ffmpeg_args, text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    try:
        length = get_video_length(file_path)
        re_parser = re.compile(r"(\w+)=\s*([^\s]+)")
        percent = 0.0
        results = {}

        first_time = time.monotonic()
        for line in process.stdout:
            if 'time=' in line:
                control_time = time.monotonic()
                d_line = dict(re_parser.findall(line))
                try:
                    # Throttle UI updates to 0.5s to prevent flickering
                    if not (control_time - first_time >= 0.5):
                        continue
                    h, m, s = d_line['time'].split(':')
                    raw_time = round((int(h) * 3600) +
                                     (int(m) * 60) + float(s), 2)
                    percent = min(100, (raw_time/length) * 100)
                    yield {'percent': round(percent, 2),
                           'final': None}
                    first_time = time.monotonic()
                except ValueError:
                    pass
                continue

            for key, regex in patterns.items():
                res = regex.search(line)
                if res:
                    results[key] = float(res.group(1))

        match mode:
            case 'fast':
                ssim_val = results.get('ssim', None)
                psnr_val = results.get('psnr', None)
                if ssim_val is not None and psnr_val is not None:
                    percent = 100.0

                    ssim_min = min(0.90, ssim_val)
                    ssim_max = max(1.0, ssim_val)

                    psnr_min = min(20, psnr_val)
                    psnr_max = max(45, psnr_val)

                    ssim = 0 if ssim_val <= 0.9 else (
                        ssim_val - ssim_min) / (ssim_max - ssim_min)
                    psnr = 0 if psnr_val <= 20 else (
                        psnr_val - psnr_min) / (psnr_max - psnr_min)

                    yield {'percent': percent,
                           'final': f'{round((((ssim + psnr) / 2) * 100), 2)}%'}
                else:
                    yield {'percent': None, 'final': None}
            case 'deep':
                percent = 100.0
                vmaf_val = results.get('vmaf', None)
                if vmaf_val is not None:
                    yield {'percent': percent,
                           'final': f"{round(vmaf_val, 2)}%"}
                else:
                    yield {'percent': None, 'final': None}
    except Exception as e:
        yield {'percent': None, 'final': None, 'error': str(e)}
    finally:
        process.stdout.close()

        if process.poll() is None:
            process.terminate()

        process.wait()
