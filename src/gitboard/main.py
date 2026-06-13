import argparse
import logging
import re

from gitboard.tui.app import GitBoardApp

logger = logging.getLogger("gitboard")


def parse_repo_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")

    patterns = [
        r"https?://github\.com/([^/]+)/([^/?#]+?)(?:\.git)?(?:\?.*)?(?:/.*)?$",
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        r"^github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$",
        r"^([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1), m.group(2).removesuffix(".git")

    raise ValueError(f"Could not parse GitHub URL: {url}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gitboard",
        description="Terminal User Interface client for GitHub",
    )
    parser.add_argument(
        "repo",
        help="GitHub repository (e.g., https://github.com/owner/name or owner/name)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        owner, name = parse_repo_url(args.repo)
    except ValueError as e:
        logger.error(e)
        return 1

    app = GitBoardApp(owner=owner, name=name)
    return app.run()
