from datetime import datetime
from pathlib import Path

from vidqueue import utils
from vidqueue.config import CONFIG
from vidqueue.core import ffmpeg_runner, queue_manager
from vidqueue.video_analyzer import analyze


def process_file(file, args, extra: dict, date_now: str,
                 total_files: list) -> int:
    """Convert a single media file using ffmpeg."""
    name = file.name

    if not utils.is_supported_file(file):
        print(f'Unsupported file: {name}')
        if len(total_files) != 1:
            utils.log_corrupted(date_now, f'Unsupported file: {name}')
            return 1
        return 1

    clean_kwargs = utils.build_ffmpeg_kwargs(file, args)

    cmd = ffmpeg_runner.prep_ffmpeg(**clean_kwargs, **extra)

    if cmd is None:
        return 1

    if not utils.convert_video(clean_kwargs['file_path'], cmd):
        utils.log_corrupted(date_now, f'Failed to convert: {name}')
        return 1
    return 0


def run_mode(args, total_files: list[Path]) -> int:
    """Run conversion mode: validate output path and process all target
       files."""
    if args.output_path.suffix:
        print("The output path must be a directory, not a file.")
        return 1

    # create a folder for converted recordings if not exists
    utils.check_dest_path(args.output_path)

    extra = {}
    if args.kwargs:
        extra = utils.parse_kwargs(args.kwargs)

    remaining_files = total_files.copy()
    queue_manager.save_queue_state(
        remaining_files, args.output_path, {
            'codec': args.codec, 'gpu': args.gpu}, extra
    )

    for file in total_files:

        date_now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
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

        remaining_files.pop(0)
        queue_manager.save_queue_state(
            remaining_files, args.output_path, {
                'codec': args.codec, 'gpu': args.gpu}, extra
        )

    queue_manager.clear_queue()
    return 0


def list_mode(total_files: list[Path]) -> int:
    """Print a numbered list of target files to stdout."""
    for file in utils.show_list(total_files):
        print(file)
    return 0


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
        folder_log_path = CONFIG["paths"]["log_analyze_path"]
        file_name = f"{args.input_path.stem}.log"
        report_path = Path(f"{folder_log_path}/{file_name}")
        with open(report_path, 'w', encoding="UTF-8") as f:
            f.write(
                f"file: {args.input_path.name} -> {args.output_path.name}\n")
            f.write(f"scan mode: {args.intensity}\n")
            f.write(f"result: {res}")

    return 0


def resume_mode() -> int:
    load_queue = queue_manager.load_queue()

    if load_queue is None:
        print("File isn't exist")
        return 0

    video_list = load_queue['videos_list'].copy()
    output_path = load_queue['output_path']
    ffmpeg_settings = load_queue['ffmpeg_settings']
    codec = ffmpeg_settings.get('codec') or 'libx264'
    is_gpu = ffmpeg_settings.get('gpu') or False
    extra = ffmpeg_settings.get('kwargs') or {}

    has_errors = False

    while video_list:
        date_now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        act_video = Path(video_list[-1])
        new_file_path = Path(output_path) / act_video.name
        act_width = ffmpeg_runner.get_video_width(Path(act_video))

        current_cmd = ffmpeg_runner.prep_ffmpeg(
            file_path=act_video,
            new_file_path=new_file_path,
            width=act_width,
            codec=codec,
            is_gpu=is_gpu,
            **extra
        )

        if not current_cmd:
            return 1

        if not utils.convert_video(act_video, current_cmd):
            utils.log_corrupted(date_now, f'Failed to convert: {act_video}')
            has_errors = True

        video_list.pop()
        queue_manager.save_queue_state(
            video_list,
            Path(output_path),
            {'codec': codec, 'gpu': is_gpu},
            extra=extra
        )
    queue_manager.clear_queue()
    return 1 if has_errors else 0
