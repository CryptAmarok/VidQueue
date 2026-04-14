from pathlib import Path


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
    return file_path.is_file() and file_path.suffix.lower() in SUFFIX_FORMATS


def check_dest_path(path: Path) -> None:
    """Check whether path is exists, if not, create it"""
    if not path.is_dir():
        path.mkdir(parents=True, exist_ok=True)
