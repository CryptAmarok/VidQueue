# VidQueue ![Version](https://img.shields.io/badge/version-0.3.1-blue)
>A Python CLI tool for converting recordings, powered by FFmpeg.

## Why?
Processing multiple video files manually is slow and repetitive.
VidQueue introduces a queue-based approach to automate and manage video processing tasks.
Many raw recordings are very large, even though they could take up much less space. 
FFmpeg requires studying complex documentation even for basic use, 
while VidQueue simplifies these instructions into a user-friendly CLI.

## Features
- Automated batch conversion of video files via FFmpeg integration.
- Simplified command-line usage for the ffmpeg tool.
- Ability to create queues for converting multiple videos.
- Intuitive monitoring of the conversion process status
- Queue-based video processing
- Supports multiple modes (run, list)
- CLI interface
- Built on top of ffmpeg
- Quality analysis using PSNR, SSIM, and VMAF metrics with simplified scoring

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
py main.py <mode> [arguments]
```
### Linux/Mac
```bash
python3 main.py <mode> [arguments]
```
### Syntax
Run mode
```bash
py main.py run <source_path> <destination_directory> [options]
```
List mode
```bash
py main.py list <source_path> [options]
```
> Note:<br>
> If a path contains spaces and is not wrapped in quotation marks, the shell interprets each space as a separator.
This means the system treats each part of the path as a separate argument. For example, `C:/My Videos/file.mp4` would be seen as two distinct inputs:
> 1. `C:/My`
> 2. `Videos/file.mp4`

### Example
Run mode:
> Convert all videos from a directory using H.265 codec with crf=20
```bash
py main.py run "C:/Videos" "C:/Output" -c h265 -k crf=20 preset=slow
```

List mode:
> Show the first 10 files that would be processed
```bash
py main.py list "C:/Videos" -s 10
```

Analyze mode:
> Analyze two video recordings to compare quality. VidQueue uses a weighted algorithm to translate technical metrics into a readable percentage score
```bash
py main.py analyze "C:/Videos/original.mp4" "C:/Videos/converted.mp4" deep
```
#### Quality Scoring
**Fast**: Uses PSNR/SSIM for rapid feedback.
> The final quality percentage is calculated using normalized PSNR and SSIM values. Any output with an SSIM below 0.90 is considered a failed conversion and results in a 0% score.

**Normalization thresholds**:

SSIM: **0.90** (0%) to **1.00** (100%)<br>
PSNR: **20dB** (0%) to **45dB** (100%)

**Deep**: Uses VMAF for high-precision perceptual analysis.
> Unlike standard metrics, VMAF predicts how the human eye perceives quality, making it the industry standard for detecting artifacts that mathematical models might miss.

**NOTE:** 

Deep analysis is computationally expensive and takes significantly longer to complete than the fast option

### Arguments and Options

| Argument/Flag | Description | Applicable Mode | Requirement |
| --- | :--- | :---: | :---: |
| **Modes** | | | |
| `run` | Starts the video conversion queue or single file. | N/A | Required |
| `list` | Lists the files that would be processed without converting them. | N/A | Required |
| `analyze` | Analyze two video recordings and display the quality score. | N/A | Required |
| **Positional Arguments** | | |
| `<source_path>` | Full path to the input video file or videos dir (If a directory is provided, the program will recursively process all supported video files within it). | `run`, `list`| Required |
| `<destination_directory>` | Path to the output folder. If the directory doesn't exist, it will be created automatically. | `run` | Required |
| `<source_file>` | Source file path. | `analyze` | Required |
| `<destination_file>` | Converted file path. | `analyze` | Required |
| `<intensity>` | Scanning depth/intensity (e.g. fast, deep). Default: fast. `fast` - SSIM, PSNR. `deep` - VMAF | `analyze` | Optional |
| **Conversion Options** | |
| `-c`, `--codec` | Select a supported FFmpeg codec from the provided list. | `run` | Optional |
| `-g`, `--gpu` | Enable GPU acceleration (recommended for 4K resolutions and above). | `run` | Optional |
| `-s`, `--select` | Select files from a directory. <br>**Run mode:** [count] or [start count] (e.g., 5 for first 5, 10 5 for 5 files starting from the 10th) <br>**List mode:** Provide [count] only (e.g., 5). | `run`, `list` | Optional |
| `-k`, `--kwargs` | Additional FFmpeg parameters (e.g., `crf=23`, `preset=medium`). *Do not use quotation marks. Separate multiple pairs with spaces (e.g. `-k crf=23 preset=medium`)*. | `run` | Optional |
| `-l`, `--log` | Generate a JSON report of the analysis. | `analyze` | Optional |
| **System Information** | | |
| `-h`, `--help` | Show the help message and exit. | Global | Optional |
| `-v`, `--version` | Show program's version number and exit. | Global | Optional |

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
