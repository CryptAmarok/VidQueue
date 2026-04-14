import argparse
import ast
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import ffmpeg_runner
import media_utils
from config_loader import CONFIG

GPU = CONFIG['hardware']['gpu']

__version__ = CONFIG['project']['version']


def _parse_value(value: str) -> Any:
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


def show_list(files: list) -> Generator[str, None, None]:
    list_length = len(files)
    zeros = int(math.log10(list_length)) + 2 if list_length > 0 else 1
    for index, value in enumerate(files):
        yield f'{(str(index + 1) + "."):>{zeros}} - {value}'


def main() -> int:
    parser = argparse.ArgumentParser(
        description='VidQueue - Automate your video processing queue')
    parser.add_argument(
        '-v', '--version', action='version',
        version=f'%(prog)s {__version__}'
    )
    subparser = parser.add_subparsers(dest='mode', required=True)

    # Run mode
    parser_run = subparser.add_parser(
        'run', help="Run the video conversion queue")
    parser_run.add_argument(
        "input_path", type=Path,
        help=("path to the file or folder with the original recording")
    )
    parser_run.add_argument(
        "output_path", type=Path,
        help=("path to the folder where the converted recording will be saved")
    )
    parser_run.add_argument(
        '-c', '--codec', type=str, default=None,
        help=("Specify video codec (e.g., libx264, h264_nvenc)")
    )
    parser_run.add_argument(
        '-g', '--gpu', action='store_true',
        help=("Enable GPU hardware acceleration")
    )
    parser_run.add_argument(
        '-s', '--select', nargs='+', type=lambda x: abs(int(x)),
        help=("Select files: [count] OR [start count] (e.g., '5', '15 10')")
    )
    parser_run.add_argument(
        '-k', '--kwargs', nargs="*",
        help=('extra params (e.g. "crf=24" or "b:a=128k") must always use '
              'the "=" symbol!')
    )

    # list mode
    parser_list = subparser.add_parser('list')
    parser_list.add_argument(
        "input_path", type=Path,
        help=("path to the file or folder with the original recording")
    )
    parser_list.add_argument(
        '-s', '--select', nargs=1, type=lambda x: abs(int(x)),
        help=("Select files: [count]")
    )
    args = parser.parse_args()

    # Check input types as booleans
    is_input_dir = args.input_path.is_dir()
    # Safely extract '-s' args and force positive values to prevent slicing bugs
    select_val = getattr(args, 'select', None)

    if select_val and len(select_val) > 2:
        parser.error("argument -s/--select: expected at most 2 arguments.")

    if not ffmpeg_runner.is_ffmpeg_installed():
        print("FFmpeg not installed")
        return 1

    if not is_input_dir and not media_utils.is_supported_file(args.input_path):
        print("The video is not supported.")
        return 1

    if is_input_dir:
        # Find all supported files and sort them from largest to smallest
        all_paths = list(Path(args.input_path).rglob('*'))
        files = [
            f for f in all_paths
            if f.is_file() and media_utils.is_supported_file(f)
        ]
        files.sort(key=lambda f: f.stat().st_size, reverse=True)
        # Check if --select is set
        if select_val and len(select_val) == 1:
            largest_files = files[:select_val[0]]
        elif select_val and len(select_val) == 2:
            start_idx = select_val[0] - 1
            count = select_val[1]
            end_idx = start_idx + count

            largest_files = files[start_idx:end_idx]
        else:
            largest_files = files

    else:
        largest_files = [args.input_path]

    match args.mode:

        case 'run':
            if args.output_path.suffix:
                print("The output path must be a directory, not a file.")
                return 1

            # create a folder for converted recordings if not exists
            media_utils.check_dest_path(args.output_path)

            extra = {}
            if args.kwargs:
                extra = parse_kwargs(args.kwargs)

            date_now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            for file in largest_files:

                name = file.name

                if not media_utils.is_supported_file(file):
                    print(f'Unsupported file: {name}')
                    if len(largest_files) != 1:
                        with open(f'{date_now}_corrupted.txt', 'a',
                                  encoding='utf-8') as f:
                            f.write(f'Unsupported file: {name}\n')
                        continue
                    return 1

                width = ffmpeg_runner.get_video_width(file)

                ffmpeg_kwargs = {
                    "file_path": file,
                    "new_file_path": args.output_path / name,
                    "width": width,
                    "codec": args.codec,
                    "gpu": args.gpu,
                    "gpu_vendor": GPU,
                }

                clean_kwargs = {k: v for k, v in ffmpeg_kwargs.items()
                                if v is not None}

                cmd = ffmpeg_runner.prep_ffmpeg(**clean_kwargs, **extra)

                if cmd is None:
                    return 1

                print(clean_kwargs['file_path'].stem)
                completed = False
                for process in ffmpeg_runner.run_ffmpeg(cmd):
                    print(
                        f"\r{process['percent']:.02f}% -- "
                        f"ETA: {process['time_left']} -- "
                        f"{process['bitrate']:<15}",
                        end='', flush=True
                    )
                    if process['percent'] == 100:
                        completed = True
                if completed:
                    print('\nConverted!')
                else:
                    print('Unconverted!')
                    with open(f'{date_now}_corrupted.txt', 'a',
                              encoding='utf-8') as f:
                        f.write(f'Failed to convert: {name}\n')

        case 'list':
            for file in show_list(largest_files):
                print(file)
        case _:
            parser.print_help()


if __name__ == '__main__':
    main()
