# VidQueue ![Version](https://img.shields.io/badge/version-0.1.0-blue)
>A Python CLI tool for converting recordings, powered by FFmpeg.

## Features
- Automated batch conversion of video files via FFmpeg integration.
- Simplified command-line usage for the ffmpeg tool.
- Ability to create queues for converting multiple videos.
- Intuitive monitoring of the conversion process status

## Installation

### Prerequisites
- **Python 3.14+**: The project was built and tested using Python 3.14.0 (64-bit). 
- **FFmpeg**: This tool is a wrapper for FFmpeg. You must have it installed and added to your system's PATH.
  - Download from the official website: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
### Build and Setup
1. Clone the repository to your local machine:
```bash
git clone https://github.com/CryptAmarok/VidQueue.git
```
2. Navigate to the project directory:
```bash
cd VidQueue
```
3. Ensure main.py has execute permissions (if applicable). No external packages via pip are required (in this version).

## Usage
The main logic is located in `main.py`. The application uses argparse to handle inputs. Arguments must be provided directly after the script name:
### Windows:
```bash
py main.py [arguments]
```
### Linux/Mac
```bash
python3 main.py [arguments]
```
### Syntax
```bash
py main.py <source_path> <destination_directory> [options]
```
### Mentor Moment
If a path contains spaces and is not enclosed in quotation marks, the shell (terminal) interprets the space as a delimiter.
This means the system treats each part of the path as a separate argument. For example, `C:/My Videos/file.mp4` would be seen as two distinct inputs:
1. `C:/My`
2. `Videos/file.mp4`

### Arguments and Options

| Argument/Flag | Decription | Requirement |
| --- | :--- | :---: |
| **Positional Arguments** | | |
| `<source_path>` | Full path to the input video file or videos dir (If we end up with a folder, the program will extract all the files that are in it) | Required |
| `<destination_directory>` | Path to the output folder. If the directory doesn't exist, it will be created automatically. | Required |
| **Conversion Options** | | |
| `-c`, `--codec` | Select a supported FFmpeg codec from the provided list. | Optional |
| `-g`, `--gpu` | Enable GPU acceleration (recommended for 4K resolutions and above). | Optional |
| `-r`, `--num_recordings` | Limit the number of recordings to be processed from the source. | Optional |
| `-k`, `--kwargs` | Additional FFmpeg parameters (e.g., `crf=23`, `preset=medium`). *Do not use quotation marks. Separate multiple pairs with spaces*. | Optional |
| **System Information** | | |
| `-h`, `--help` | Show the help message and exit. | Optional |
| `-v`, `--version` | Show program's version number and exit. | Optional |

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
