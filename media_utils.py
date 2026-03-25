import subprocess
import pathlib
import shutil
import re

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


def get_video_length(file_path):
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
    ffmpeg_args = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'info']

    if is_gpu and width >= 3840:  # for 4k or higher quality
        match gpu_vendor.upper():
            case 'NVIDIA':
                ffmpeg_args.extend(['-hwaccel', 'cuda'])
            case 'AMD':
                ffmpeg_args.extend(['-hwaccel', 'd3d11va'])
            case 'INTEL':
                ffmpeg_args.extend(['-hwaccel', 'qsv'])

    ffmpeg_args.extend([
        '-i', str(file_path),
        '-c:v', codec,
    ])

    for key, value in ffmpeg_params.items():
        if isinstance(value, bool):  # check whether it is bool
            if value is True:  # if False ignore
                ffmpeg_args.append(f'-{key}')
        ffmpeg_args.append(f'-{key}')
        ffmpeg_args.append(str(value))

    ffmpeg_args.append(str(new_file_path))

    test_prompt = ffmpeg_args[:-1] + ['-frames:v', '1', '-f', 'null', '-']
    try:
        subprocess.run(test_prompt, capture_output=True, text=True, check=True)
        return ffmpeg_args
    except subprocess.CalledProcessError as e:
        print(f'ERROR: {e.stderr.strip()}')
        return None


def run_ffmpeg(cmd_params: list[str]) -> None:
    """
    Run FFmpeg and show a real-time progress bar in the terminal.

    This function parses FFmpeg output to show percentage, time, and ETA.
    It is recommended to use 'prep_ffmpeg' to create the 'cmd_params' list 
    before calling this function to ensure the command is valid.

    Args:
        cmd_params (list[str]): Valid list of FFmpeg arguments.
    """

    if not cmd_params:
        return
    try:
        idx = cmd_params.index('-i')
        path = pathlib.Path(cmd_params[idx + 1])

        file_name = path.name
        video_length = get_video_length(path)

        process = subprocess.Popen(cmd_params, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   encoding='utf-8')

        required = ('time', 'bitrate', 'speed')
        for line in process.stdout:
            f_line = re.search(r'time=\d{2}', line)
            if f_line:
                c_line = line.replace('=', '= ')
                parts = c_line.split()
                d_line = {
                    key.strip('='): value for key,
                    value in zip(parts[0::2], parts[1::2])
                }
                if not all(key in d_line for key in required):
                    continue
                if ':' not in d_line['time']:
                    continue
                h, m, s = d_line['time'].split(':')
                raw_time = round((int(h) * 3600) + (int(m) * 60) + float(s), 2)

                percent = min(100.0, (raw_time/video_length * 100))
                str_time = d_line['speed'][:-1]
                speed_val = float(str_time) if str_time not in (
                    '0', '0.0', 'N/A') else 1.0
                time_left = (video_length - raw_time) / \
                    float(speed_val)
                time_repr = f'{int(time_left // 3600)}:'\
                    f'{int((time_left % 3600) // 60):02d}:{(time_left % 60):02.0f}'

                print(f'\rcompleted: {percent:.2f}% | {h:02}:{m:02}:{s:02} '
                      f'| left: {time_repr} | bitrate: {d_line["bitrate"]:<15}',
                      end='', flush=True)

        process.wait()
        print()
        if process.returncode == 0:
            print(f'\nVideo {file_name} completed! Saved in: {cmd_params[-1]}')
        else:
            print(f'\nFFmpeg finished with error code: {process.returncode}')

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f'\nUnexpected Error: {e}')
