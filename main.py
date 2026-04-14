from datetime import datetime
from pathlib import Path

import ffmpeg_runner
import media_utils
from cli import parse_arguments
from config_loader import CONFIG
from utils import parse_kwargs, show_list

GPU = CONFIG['hardware']['gpu']


def main() -> int:

    args = parse_arguments()

    # Check input types as booleans
    is_input_dir = args.input_path.is_dir()

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
        if args.select and len(args.select) == 1:
            largest_files = files[:args.select[0]]
        elif args.select and len(args.select) == 2:
            start_idx = args.select[0] - 1
            count = args.select[1]
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
    return 0


if __name__ == '__main__':
    main()
