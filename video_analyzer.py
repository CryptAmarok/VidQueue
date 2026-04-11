from pathlib import Path
import re
import subprocess
from typing import Generator

from media_utils import get_video_length


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

    if not file_path.exists() or not compressed_file_path.exists():
        raise ValueError("Input file don't exists. Check paths")

    patterns = {}
    mode = mode.lower().strip() if isinstance(mode, str) else mode
    if mode == 'fast':
        filters = "[0:v][1:v]ssim;[0:v][1:v]psnr"
        re_ssim = re.compile(r"All:(\d+\.\d+)")
        re_psnr = re.compile(r"average:(\d+\.\d+)")
        patterns["ssim"] = re_ssim
        patterns["psnr"] = re_psnr
    elif mode == 'deep':
        filters = "libvmaf"
        re_vmaf = re.compile(r"score: (\d+\.\d+)")
        patterns["vmaf"] = re_vmaf
    else:
        raise ValueError(f"Invalid mode: '{mode}'. Expected 'fast' or 'deep'.")

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
        for line in process.stdout:
            if 'time=' in line:
                d_line = dict(re_parser.findall(line))
                try:
                    h, m, s = d_line['time'].split(':')
                    raw_time = round((int(h) * 3600) +
                                     (int(m) * 60) + float(s), 2)
                    percent = min(100, (raw_time/length) * 100)
                    yield {'percent': round(percent, 2),
                           'final': None}
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