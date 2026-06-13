import logging
from pathlib import Path

from gitboard.config import CONFIG_DIR

logger = logging.getLogger(__name__)

_SERVICE_NAME = "gitboard"


def _get_token_file() -> Path:
    return CONFIG_DIR / "token"


def get_pat() -> str | None:
    import os

    env_token = os.environ.get("GITBOARD_PAT")
    if env_token:
        logger.debug("using GITBOARD_PAT from environment")
        return env_token

    try:
        import keyring
        token = keyring.get_password(_SERVICE_NAME, "github_pat")
        if token:
            return token
    except Exception as exc:
        logger.debug("keyring unavailable (%s), trying file fallback", exc)

    token_file = _get_token_file()
    if token_file.exists():
        try:
            return token_file.read_text().strip()
        except OSError as exc:
            logger.debug("could not read token file: %s", exc)

    return None


def store_pat(token: str) -> None:
    try:
        import keyring
        keyring.set_password(_SERVICE_NAME, "github_pat", token)
        logger.info("token stored in OS keyring")
        return
    except Exception as exc:
        logger.debug("keyring unavailable (%s), falling back to file", exc)

    token_file = _get_token_file()
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.touch(mode=0o600, exist_ok=True)
    token_file.chmod(0o600)
    token_file.write_text(token)
    logger.info("token stored in %s", token_file)


def clear_pat() -> None:
    try:
        import keyring
        keyring.delete_password(_SERVICE_NAME, "github_pat")
    except Exception:
        pass
    token_file = _get_token_file()
    if token_file.exists():
        token_file.unlink()
    logger.info("token cleared")


def is_authenticated() -> bool:
    return get_pat() is not None
