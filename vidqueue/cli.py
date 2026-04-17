import argparse
from pathlib import Path

from vidqueue.config import CONFIG


__version__ = CONFIG['project']['version']


def parse_arguments():
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
    '''
    Safely extract '-s' args and force positive values to prevent 
    slicing bugs
    '''
    select_val = getattr(args, 'select', None)
    if select_val and len(select_val) > 2:
        parser.error("argument -s/--select: expected at most 2 arguments.")

    return args
