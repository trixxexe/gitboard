from pathlib import Path
import os


def _get_cache_dir() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "gitboard"
    return Path.home() / ".cache" / "gitboard"


def _get_config_dir() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "gitboard"
    return Path.home() / ".config" / "gitboard"


CACHE_DIR = _get_cache_dir()
CONFIG_DIR = _get_config_dir()
CACHE_DB_PATH = CACHE_DIR / "cache.db"
CACHE_TTL = 300

GRAPHQL_URL = "https://api.github.com/graphql"
REST_API_URL = "https://api.github.com"
USER_AGENT = "gitboard/0.1.0"
