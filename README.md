# gitboard

A visually rich, pip-installable Terminal User Interface (TUI) client for GitHub. Browse repositories, view source code with syntax highlighting, inspect issues, and monitor GitHub Actions workflows — all from your terminal.

## Features

- **File Tree Browser** — navigate repository files and directories in a collapsible tree
- **Syntax-Highlighted Code Viewer** — powered by Rich for 100+ languages
- **README Rendering** — Markdown rendered directly in the terminal
- **Issues Overview** — view open issues with author and status badges
- **GitHub Actions** — monitor workflow runs, branches, and pass/fail status
- **Language Breakdown** — see repository language distribution at a glance
- **Contributor Stats** — top contributors with commit counts
- **Offline Caching** — previously fetched data available when rate-limited or offline
- **Asynchronous Loading** — all network calls run in background workers; the UI stays responsive
- **Graceful Rate-Limit Handling** — falls back to cached data when API limits are hit
- **PAT Authentication** — optional Personal Access Token for private repos and higher rate limits
- **Termux Compatible** — runs on headless Linux and Android (Termux) environments

## Installation

```bash
pip install gitboard
```

## Usage

```bash
gitboard <repository-url>
```

The repository URL can be in any of these formats:

```bash
# Full HTTPS URL
gitboard https://github.com/owner/repo

# SSH-style
gitboard git@github.com:owner/repo

# Shorthand
gitboard owner/repo
```

### Options

```
gitboard <repo> [--verbose | -v]
```

| Flag | Description |
|------|-------------|
| `--verbose`, `-v` | Enable debug logging |

### Authentication

Set a GitHub Personal Access Token (PAT) via environment variable:

```bash
export GITBOARD_PAT=ghp_xxxxxxxxxxxx
gitboard owner/repo
```

Or authenticate interactively by pressing `a` inside the app.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `Ctrl+C` | Emergency quit |
| `a` | Open authentication dialog |
| `c` | Clone repository |
| `f` | Fork repository |
| `i` | New issue |

## License

MIT License — see [LICENSE](LICENSE) for details.
