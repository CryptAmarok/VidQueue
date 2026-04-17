"""Load the project configuration from config.toml.

Uses tomllib to parse the TOML file into the CONFIG dictionary.
"""
import tomllib
from pathlib import Path

_CONFIG_PATH = Path('config.toml')
with _CONFIG_PATH.open('rb') as f:
    CONFIG = tomllib.load(f)