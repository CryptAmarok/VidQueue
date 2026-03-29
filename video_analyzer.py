import pathlib
import re
import subprocess
from typing import Generator, Union

from media_utils import get_video_length


def analyze_fast(
        file_path: pathlib.Path,
        compressed_file_path: pathlib.Path) -> Generator[
        dict[str, Union[str | float | None]], None, None]:
    """
    Analyzes the quality of a compressed video against the original 
    using SSIM and PSNR metrics.

    This function runs FFmpeg as a subprocess and acts as a generator, 
    yielding real-time progress updates based on the processed video time.
    Upon completion, it calculates and yields a normalized overall quality
    score as a percentage. It ensures safe and complete termination of 
    the subprocess regardless of the execution flow.

    Note:
        The two files must be of the same resolution.

    Args:
        file_path (pathlib.Path): Path to the original (reference) video
            file.
        compressed_file_path (pathlib.Path): Path to the compressed 
            video file. Must match the resolution of the original file.

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
        ValueError: If either the original or compressed input file does 
            not exist.
    """

    if not file_path.exists() or not compressed_file_path.exists():
        raise ValueError("Input files don't exists. Check paths")

    filters = "[0:v][1:v]ssim;[0:v][1:v]psnr"

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
        re_ssim = re.compile(r"All:(\d+\.\d+)")
        re_psnr = re.compile(r"average:(\d+\.\d+)")
        ssim_result, psnr_result = None, None
        percent = 0.0
        for line in process.stdout:
            d_line = dict(re_parser.findall(line))
            if d_line.get('time', None):
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

            if 'Parsed_ssim_0' in line:
                res = re_ssim.search(line)
                if res:
                    ssim_result = float(res.group(1))

            elif 'Parsed_psnr_1' in line:
                res = re_psnr.search(line)
                if res:
                    psnr_result = float(res.group(1))

        if ssim_result is not None and psnr_result is not None:
            percent = 100.0

            ssim_min = min(0.90, ssim_result)
            ssim_max = max(1.0, ssim_result)

            psnr_min = min(20, psnr_result)
            psnr_max = max(45, psnr_result)

            ssim = 0 if ssim_result <= 0.9 else (
                ssim_result - ssim_min) / (ssim_max - ssim_min)
            psnr = 0 if psnr_result <= 20 else (
                psnr_result - psnr_min) / (psnr_max - psnr_min)

            yield {'percent': percent,
                   'final': f'{round((((ssim + psnr) / 2) * 100), 2)}%'}
        else:
            yield {'percent': None, 'final': None}
    except Exception as e:
        yield {'percent': None, 'final': None, 'error': str(e)}
    finally:
        process.stdout.close()

        if process.poll() is None:
            process.terminate()

        process.wait()
