from vidqueue.cli import parse_arguments
from vidqueue.utils import (get_target_files, list_mode, run_mode,
                            validate_environment)


def main() -> int:
    """Entry point of the application. Returns exit code."""
    args = parse_arguments()

    if validate_environment(args):
        return 1

    largest_files = get_target_files(args.input_path, args.select)

    match args.mode:

        case 'run':
            return run_mode(args, largest_files)
        case 'list':
            return list_mode(largest_files)
    return 0


if __name__ == '__main__':
    main()
