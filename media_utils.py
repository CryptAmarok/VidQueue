import pathlib
import re
import shutil
import subprocess
import time
from typing import Generator, Union

# TODO: Extract supported formats to json file in future to separate
#       configuration from logic.
SUFFIX_FORMATS = {
    '.avi': 'avi',
    '.flv': 'flv',
    '.m4v': 'm4v',
    '.mp4': 'mp4',
    '.mkv': 'mkv',
    '.mov': 'mov',
    '.mpg': 'mpg',
    '.mpeg': 'mpeg',
    '.webm': 'webm',
    '.wmv': 'wmv',
}

# TODO: same as Suffix
GPU = 'NVIDIA'


class InvalidMediaError(Exception):
    """Raised when file is corrupted or unreadable"""
    pass


def is_ffmpeg_installed() -> bool:
    """Check whether ffmpeg is installed"""
    return bool(shutil.which("ffmpeg"))


def is_supported_file(file_path: pathlib.Path) -> bool:
    """Validates whether the input file exists
        and has a supported extension."""
    if file_path.is_file() and file_path.suffix.lower() in SUFFIX_FORMATS:
        return True
    return False


def check_dest_path(path: pathlib.Path) -> None:
    path = path.parent
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)


def get_video_width(file_path: pathlib.Path) -> int:
    """Return the total width of the video file in pixels."""
    commands = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width',
        '-of', 'default=nw=1:nk=1',
        str(file_path)
    ]
    try:
        result = subprocess.run(commands, capture_output=True,
                                text=True, check=True).stdout
        return int(result)

    except subprocess.CalledProcessError as e:
        error_msg = f"ERROR: ffprobe encountered a problem with {file_path}"
        raise InvalidMediaError(error_msg) from e

    except ValueError as e:
        error_msg = "ERROR: ffprobe didn't return a valid number " \
            f"for {file_path}"
        raise ValueError(error_msg) from e


def get_video_length(file_path: pathlib. Path):
    """Returns the total length of the video file in seconds."""
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", file_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    return float(result.stdout)


def prep_ffmpeg(file_path: pathlib.Path, new_file_path: pathlib.Path,
                width: int, codec: str = 'libx264', is_gpu: bool = False,
                gpu_vendor: str = GPU, **ffmpeg_params) -> list[str] | None:
    """
    Prepare and check an FFmpeg command for video processing.

    This function builds a list of FFmpeg arguments using the input/output
    paths, video width, codec, and GPU settings. You can add extra FFmpeg flags
    using keyword arguments. If the parameters are invalid, it returns None.

    Args:
        file_path (pathlib.Path): Path to the input video file.
        new_file_path (pathlib.Path): Path for the output video file.
        width (int): Original video width in pixels (used to trigger
            GPU logic).
        codec (str, optional): Video codec to use. Defaults to 'libx264'.
        is_gpu (bool, optional): Whether to use GPU acceleration. Defaults
            to False.
        gpu_vendor (str, optional): GPU brand (NVIDIA, AMD, INTEL).
            Defaults to the global `GPU` variable.
        **ffmpeg_params: Extra FFmpeg flags. Boolean True values add only the
            flag (e.g. an=True adds '-an'), while other values add both the
            flag and the value.

    Returns:
        list[str] | None: A list of command arguments for 'subprocess',
        or None if the parameters are wrong.

    Example:
        >>> import pathlib
        >>> input_vid = pathlib.Path("input.mp4")
        >>> output_vid = pathlib.Path("output.mp4")
        >>> # Dynamics dictionary
        >>> custom_params = {
        ...     'preset': 'fast',
        ...     'crf': 23,
        ...     'an': True,  # This will add '-an' to remove audio
        ...     'b:a': '128k'
        ... }
        >>> prep_ffmpeg(input_vid, output_vid, width=1920, **custom_params)
    """
    ffmpeg_prompt = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'info']

    if is_gpu and width >= 3840:  # for 4k or higher quality
        match gpu_vendor.upper():
            case 'NVIDIA':
                ffmpeg_prompt.extend(['-hwaccel', 'cuda'])
            case 'AMD':
                ffmpeg_prompt.extend(['-hwaccel', 'd3d11va'])
            case 'INTEL':
                ffmpeg_prompt.extend(['-hwaccel', 'qsv'])

    ffmpeg_prompt.extend([
        '-i', str(file_path),
        '-c:v', codec,
    ])

    for key, value in ffmpeg_params.items():
        if isinstance(value, bool):  # check wheteher is bool
            if value is True:  # if False ignore
                ffmpeg_prompt.append(f'-{key}')
            continue
        ffmpeg_prompt.append(f'-{key}')
        ffmpeg_prompt.append(str(value))

    ffmpeg_prompt.append(str(new_file_path))

    test_prompt = ffmpeg_prompt[:-1] + ['-frames:v', '1', '-f', 'null', '-']
    try:
        subprocess.run(test_prompt, capture_output=True, text=True, check=True)
        return ffmpeg_prompt
    except subprocess.CalledProcessError as e:
        print(f'ERROR: {e.stderr.strip()}')
        return None


def run_ffmpeg(cmd_params: list[str]) -> Generator[dict[str, Union[
        float | str]], None, None]:
    """
    Run FFmpeg as a subprocess and yield real-time progress data.

    Parses FFmpeg stdout to estimate completion percentage, remaining time,
    and current bitrate.

    Args:
        cmd_params (list[str]): FFmpeg command arguments.

    Yields:
        dict: Progress data with keys:
            - percent (float): Completion percentage. (Or 'N/A')
            - time_left (str): Estimated time remaining (Or 'N/A')
            - bitrate (str): Current bitrate (Or 'N/A').

    Raises:
        ValueError: If the 'cmd_params' list is empty.
        InvalidMediaError: If FFmpeg exits with a non-zero code.
    """

    if not cmd_params:
        raise ValueError(
            "The 'cmd_params' list is empty. Please provide"
            " valid FFmpeg arguments."
        )
    process = None
    try:
        idx = cmd_params.index('-i')
        path = pathlib.Path(cmd_params[idx + 1])

        video_length = get_video_length(path)

        process = subprocess.Popen(cmd_params, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   encoding='utf-8')

        required = ('time', 'bitrate', 'speed')
        regex_parser = re.compile(r"(\w+)=\s*([^\s]+)")
        first_time = time.monotonic()
        for line in process.stdout:
            if 'time=' in line:
                second_time = time.monotonic()
                if not (second_time - first_time >= 1.0 or 'bitrate:' in line):
                    continue
                d_line = dict(regex_parser.findall(line))
                if not all(key in d_line for key in required):
                    continue
                if ':' not in d_line['time']:
                    continue
                h, m, s = d_line['time'].split(':')
                raw_time = round((int(h) * 3600) + (int(m) * 60) + float(s), 2)

                percent = min(100.0, (raw_time/video_length * 100))
                str_time = d_line['speed'][:-1]
                try:
                    speed_val = float(str_time)
                    if speed_val <= 0.0:
                        speed_val = 1.0
                except ValueError:
                    speed_val = 1.0
                time_left = (
                    max(0, (video_length - raw_time))
                    / float(speed_val)
                )
                time_repr = (
                    f'{int(time_left // 3600)}:'
                    f'{int((time_left % 3600) // 60):02d}:'
                    f'{(time_left % 60):02.0f}'
                )

                yield {
                    'percent': percent,
                    'time_left': time_repr,
                    'bitrate': d_line["bitrate"]
                }
                first_time = time.monotonic()

        process.wait()
        if process.returncode != 0:
            err_msg = f"FFmpeg finished with error code: {process.returncode}"
            raise InvalidMediaError(err_msg)
        try:
            if percent != 100.0:
                yield {
                    'percent': 100.0,
                    'time_left': '0:00:00',
                    'bitrate': d_line["bitrate"]
                }
        except (NameError, KeyError):
            yield {
                'percent': 'N/A',
                'time_left': 'N/A',
                'bitrate': 'N/A'
            }

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")

    except Exception as e:
        print(f'\nUnexcpeted Error: {e}')

    finally:
        if process is not None and process.poll() is None:
            process.terminate()
