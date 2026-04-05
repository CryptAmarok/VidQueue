import argparse
import ast
from datetime import datetime
from pathlib import Path
from typing import Any

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description='VidQueue - Automate your video processing queue')

    parser.add_argument(
        "input_path", type=Path,
        help=("path to the file or folder with the original recording")
    )
    parser.add_argument(
        "output_path", type=Path,
        help=("path to the folder where the converted recording will be saved")
    )
    parser.add_argument(
        '-c', '--codec', default=None
    )
    parser.add_argument(
        '-g', '--gpu', action='store_true'
    )
    parser.add_argument(
        "-r", "--num_recordings", type=int,
        help="Number of recordings to select"
    )
    parser.add_argument(
        '-k', '--kwargs', nargs="*",
        help=('etra params (e.g. "crf=24" or "b:a=128k") must always use'
              'the "=" symbol!')
    )
    parser.add_argument(
        '-v', '--version', action='version',
        version=f'%(prog)s {__version__}'
    )
    args = parser.parse_args()

    # Check input types as booleans
    is_input_dir = args.input_path.is_dir()

    if not media_utils.is_ffmpeg_installed():
        print("FFmpeg not installed")
        return 1

    if args.output_path.suffix:
        print("The output path must be a directory, not a file.")
        return 1

    # create a folder for converted recordings if not exists
    media_utils.check_dest_path(args.output_path)

    if not is_input_dir and not media_utils.is_supported_file(args.input_path):
        print("The video is not supported.")
        return 1

    if is_input_dir:
        # Find all files and sort them from largest to smallest
        all_paths = list(Path(args.input_path).rglob('*'))
        files = [f for f in all_paths if f.is_file()]
        files.sort(key=lambda f: f.stat().st_size, reverse=True)
        largest_files = files[:args.num_recordings]
    else:
        largest_files = [args.input_path]

    extra = {}
    if args.kwargs:
        extra = parse_kwargs(args.kwargs)

    date_now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    for file in largest_files:

        name = file.name

        if not media_utils.is_supported_file(file):
            print(f'Unsupported file: {name}')
            if len(largest_files) != 1:
                with open(f'{date_now}_corrupted.txt', 'a') as f:
                    f.write(f'Unsupported file: {name}\n')
                continue
            return 1

        width = media_utils.get_video_width(file)

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

        cmd = media_utils.prep_ffmpeg(**clean_kwargs, **extra)

        if cmd is None:
            return 1

        print(clean_kwargs['file_path'].stem)
        completed = False
        for process in media_utils.run_ffmpeg(cmd):
            print(
                f"\r{process['percent']:.02f}% -- "
                f"ETA: {process['time_left']} -- {process['bitrate']:<15}",
                end='', flush=True
            )
            if process['percent'] == 100:
                completed = True
        if completed:
            print('Converted!')
        else:
            print('Unconverted!')
            with open(f'{date_now}_corrupted.txt', 'a') as f:
                f.write(f'Failed to convert: {name}\n')


if __name__ == '__main__':
    main()
