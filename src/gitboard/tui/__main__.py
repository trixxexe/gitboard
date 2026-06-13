import sys
from gitboard.tui.app import GitBoardApp


def main() -> int:
    app = GitBoardApp(owner="opencode-ai", name="opencode")
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
