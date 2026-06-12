import ast
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from vidqueue.core import ffmpeg_runner
from vidqueue.video_analyzer import analyze
from vidqueue.config import CONFIG

GPU = CONFIG['hardware']['gpu']

# TODO: Extract supported formats to json file in future to separate
#       configuration from logic.
SUFFIX_FORMATS = {
    '.avi', '.flv',
    '.m4v', '.mp4',
    '.mkv', '.mov',
    '.mpg', '.mpeg',
    '.webm', '.wmv'
}


def is_supported_file(file_path: Path) -> bool:
    """Validates whether the input file exists
        and has a supported extension."""
    return file_path.suffix.lower() in SUFFIX_FORMATS


def check_dest_path(path: Path) -> None:
    """Check whether path is exists, if not, create it"""
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)


def _parse_value(value: str) -> Any:
    """Try to evaluate a string as a Python literal,
      fallback to raw string."""
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value


def parse_kwargs(kwlist: list) -> dict[str, Any]:
    """Parse a list of 'key=value' strings into a dict.
    Example: ['crf=24', 'preset=fast'] -> {'crf': 24, 'preset': 'fast'}
    """
    return {
        key: _parse_value(value)
        for arg in kwlist
        for key, value in [arg.split('=', 1)]
    }


def show_list(files: list[Path]) -> Generator[str, None, None]:
    """Yield numbered entries for each file in the list.
    """
    list_length = len(files)
    zeros = int(math.log10(list_length)) + 2 if list_length > 0 else 1
    for index, value in enumerate(files):
        yield f'{(str(index + 1) + "."):>{zeros}} - {value}'


# run mode
def get_target_files(input_path: Path,
                     select_args: list[int] | None) -> list[Path]:
    """Return a list of target media files based on input path and
    selection."""
    if input_path.is_dir():
        # Find all supported files and sort them from largest to smallest
        all_paths = list(input_path.rglob('*'))
        files = [
            f for f in all_paths
            if f.is_file() and is_supported_file(f)
        ]
        files.sort(key=lambda f: f.stat().st_size, reverse=True)
        # Check if --select is set
        if select_args and len(select_args) == 1:
            largest_files = files[:select_args[0]]
        elif select_args and len(select_args) == 2:
            start_idx = select_args[0] - 1
            count = select_args[1]
            end_idx = start_idx + count

            largest_files = files[start_idx:end_idx]
        else:
            largest_files = files

    else:
        largest_files = [input_path]

    return largest_files


def validate_environment(args) -> int:
    """Check that FFmpeg is installed and the input file is supported."""

    if not ffmpeg_runner.is_ffmpeg_installed():
        print("FFmpeg not installed")
        return 1

    # Check if the input path exists
    input_path = args.input_path
    if not input_path.exists():
        print(f"The input path: '{input_path}' doesn't exist. Check the path")
        return 1

    # Check input types as booleans
    is_input_dir = args.input_path.is_dir()
    if not is_input_dir and not is_supported_file(args.input_path):
        print("The video is not supported.")
        return 1

    return 0


def log_corrupted(date_now: str, message: str):
    """Append a message to the corrupted files log for the current
      session."""
    with open(f'{date_now}_corrupted.txt', 'a',
              encoding='utf-8') as f:
        f.write(f'{message}\n')


def build_ffmpeg_kwargs(file: Path, args) -> dict:
    """Build a cleaned kwargs dict for ffmpeg, removing None values."""
    width = ffmpeg_runner.get_video_width(file)

    ffmpeg_kwargs = {
        "file_path": file,
        "new_file_path": args.output_path / file.name,
        "width": width,
        "codec": args.codec,
        "is_gpu": args.gpu,
        "gpu_vendor": GPU,
    }

    return {k: v for k, v in ffmpeg_kwargs.items() if v is not None}


def process_file(file, args, extra: dict, date_now: str,
                 total_files: list) -> int:
    """Convert a single media file using ffmpeg."""
    name = file.name

    if not is_supported_file(file):
        print(f'Unsupported file: {name}')
        if len(total_files) != 1:
            log_corrupted(date_now, f'Unsupported file: {name}')
            return 1
        return 1

    clean_kwargs = build_ffmpeg_kwargs(file, args)

    cmd = ffmpeg_runner.prep_ffmpeg(**clean_kwargs, **extra)

    if cmd is None:
        return 1

    print(clean_kwargs['file_path'].stem)
    completed = False
    for process in ffmpeg_runner.run_ffmpeg(cmd):
        print(
            f"\r{process['percent']:.02f}% -- "
            f"ETA: {process['time_left']} -- "
            f"{process['bitrate']}\033[K",
            end='', flush=True
        )
        if process['percent'] == 100:
            completed = True
    if completed:
        print('\nConverted!')
        return 0
    print('Unconverted!')
    log_corrupted(date_now, f'Failed to convert: {name}')
    return 1


def run_mode(args, total_files: list[Path]) -> int:
    """Run conversion mode: validate output path and process all target
       files."""
    if args.output_path.suffix:
        print("The output path must be a directory, not a file.")
        return 1

    # create a folder for converted recordings if not exists
    check_dest_path(args.output_path)

    extra = {}
    if args.kwargs:
        extra = parse_kwargs(args.kwargs)

    date_now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    for file in total_files:
        try:
            process_code = process_file(
                file, args, extra, date_now, total_files)
        except KeyboardInterrupt:
            print('Program interrupted by user.')
            return 1

        if process_code:
            if len(total_files) == 1:
                return 1
            continue
    return 0


# list mode
def list_mode(total_files: list[Path]) -> None:
    """Print a numbered list of target files to stdout."""
    for file in show_list(total_files):
        print(file)


# analyze mode
def analyze_mode(args) -> int:
    """Performs video analysis and optionally saves the result to a file.

    Args:
        args (argparse.Namespace): CLI arguments containing paths and
        settings.

    Returns:
        int: 0 for success, 1 if no result was produced.
    """

    if not args.output_path.is_file():
        print(f"The output file: '{args.output_path}' doesn't "
              "exist. Check the path")
        return 1

    res = None
    for process in analyze(args.input_path, args.output_path, args.intensity):

        if process['final'] is None:
            # \033[K - clear the line to the end
            print(f"\rprocessing: {process['percent']}%\033[K",
                  end='', flush=True)
        else:
            res = process['final']
            print(f"\rquality: {res}\033[K")
    if res is None:
        return 1

    if args.log:
        # TODO: Extract filename logic
        report_path = f"{args.input_path.stem}.json"
        with open(report_path, 'w', encoding="UTF-8") as f:
            f.write(
                f"file: {args.input_path.name} -> {args.output_path.name}\n")
            f.write(f"scan mode: {args.intensity}\n")
            f.write(f"result: {res}")
    return 0
