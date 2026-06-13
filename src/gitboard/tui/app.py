from pathlib import Path
from typing import Any, Optional

import httpx
from rich.syntax import Syntax
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Footer,
    Header,
    Label,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)
from textual.widgets.tree import TreeNode

from gitboard.api import (
    AuthError,
    GithubAPIError,
    NotFoundError,
    RateLimitError,
    RepoAPIClient,
)
from gitboard.auth import get_pat, is_authenticated, store_pat
from gitboard.tui.screens import AuthScreen
from gitboard.cache import DiskCache
from gitboard.config import CACHE_TTL

BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".o", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".pyc", ".pyo", ".pyd",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg",
    ".icns", ".webp",
    ".ttf", ".otf",
})

EXTENSION_LANG: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "tsx", ".jsx": "jsx", ".html": "html", ".css": "css",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".md": "markdown", ".rs": "rust", ".go": "go",
    ".java": "java", ".rb": "ruby", ".c": "c", ".cpp": "cpp",
    ".h": "c", ".hpp": "cpp", ".sh": "bash", ".bash": "bash",
    ".toml": "toml", ".sql": "sql", ".dockerfile": "dockerfile",
    ".lock": "json", ".xml": "xml", ".kt": "kotlin",
    ".swift": "swift", ".r": "r", ".m": "objectivec",
    ".scala": "scala", ".vue": "vue", ".svelte": "svelte",
    ".php": "php", ".pl": "perl", ".lua": "lua",
    ".hs": "haskell", ".clj": "clojure", ".erl": "erlang",
    ".ex": "elixir", ".exs": "elixir",
}


class GitBoardApp(App):
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "emergency_quit", "Emergency Quit"),
        ("c", "clone", "Clone"),
        ("f", "fork", "Fork"),
        ("i", "new_issue", "New Issue"),
        ("a", "auth", "Auth"),
    ]

    def __init__(self, owner: str, name: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._repo_owner = owner
        self._repo_name = name
        self._ref = "HEAD"
        self._offline_mode = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        yield Horizontal(id="repo-header")

        with Horizontal(id="main-container"):
            with Vertical(id="left-sidebar"):
                yield Tree[dict]("Files", id="file-tree")

            with Vertical(id="center-panel"):
                with TabbedContent(id="content-tabs"):
                    with TabPane("Code", id="tab-code"):
                        yield Static("Select a file to view", id="code-viewer")
                    with TabPane("README", id="tab-readme"):
                        yield Static("Loading README...", id="readme-viewer")
                    with TabPane("Issues", id="tab-issues"):
                        yield Vertical(id="issues-list")
                    with TabPane("Actions", id="tab-actions"):
                        yield Vertical(id="actions-view")

            with Vertical(id="right-sidebar"):
                yield Static("Languages", classes="sidebar-section-title")
                yield Static("Loading...", id="languages-content")
                yield Static("Contributors", classes="sidebar-section-title")
                yield Static("Loading...", id="contributors-content")

        yield Footer()

    def on_mount(self) -> None:
        self.title = f"{self._repo_owner}/{self._repo_name}"
        if not is_authenticated():
            self.push_screen(AuthScreen(), self._on_auth_result)
        else:
            self._load_data()

    def action_emergency_quit(self) -> None:
        self.exit()

    def action_auth(self) -> None:
        self.push_screen(AuthScreen(), self._on_auth_result)

    def _on_auth_result(self, token: str | None) -> None:
        if token:
            store_pat(token)
            self.call_later(self._rebuild_and_reload)

    async def _rebuild_and_reload(self) -> None:
        try:
            header = self.query_one("#repo-header")
            await header.remove_children()
        except Exception:
            pass

        try:
            old = self.query_one("#main-container")
            await old.remove()
        except Exception:
            pass

        try:
            footer = self.query_one(Footer)
        except Exception:
            footer = None

        left = Vertical(
            Tree[dict]("Files", id="file-tree"),
            id="left-sidebar",
        )

        center = Vertical(
            TabbedContent(
                TabPane("Code", Static("Select a file to view", id="code-viewer"), id="tab-code"),
                TabPane("README", Static("Loading README...", id="readme-viewer"), id="tab-readme"),
                TabPane("Issues", Vertical(id="issues-list"), id="tab-issues"),
                TabPane("Actions", Vertical(id="actions-view"), id="tab-actions"),
                id="content-tabs",
            ),
            id="center-panel",
        )

        right = Vertical(
            Static("Languages", classes="sidebar-section-title"),
            Static("Loading...", id="languages-content"),
            Static("Contributors", classes="sidebar-section-title"),
            Static("Loading...", id="contributors-content"),
            id="right-sidebar",
        )

        container = Horizontal(left, center, right, id="main-container")

        if footer is not None:
            await self.mount(container, before=footer)
        else:
            await self.mount(container)

        try:
            self.query_one("#file-tree")
        except Exception:
            self.set_timer(0.05, self._rebuild_and_reload)
            return

        self._load_data()

    # ------------------------------------------------------------------
    #  Data loading
    # ------------------------------------------------------------------

    @work(thread=True)
    def _load_data(self) -> None:
        try:
            token = get_pat()
            client = RepoAPIClient(token=token)
            cache = DiskCache()
            cache_key = f"repo:{self._repo_owner}/{self._repo_name}"

            try:
                data = client.get_repo_data(self._repo_owner, self._repo_name)
                cache.set(cache_key, data, ttl=CACHE_TTL)

                cached_contributors = cache.get(
                    f"contrib:{self._repo_owner}/{self._repo_name}"
                )
                if not cached_contributors:
                    contributors = client.get_contributors(
                        self._repo_owner, self._repo_name
                    )
                    cache.set(
                        f"contrib:{self._repo_owner}/{self._repo_name}",
                        contributors,
                        ttl=3600,
                    )
                else:
                    contributors = cached_contributors

                cached_runs = cache.get(
                    f"runs:{self._repo_owner}/{self._repo_name}"
                )
                if not cached_runs:
                    runs = client.get_workflow_runs(
                        self._repo_owner, self._repo_name
                    )
                    cache.set(
                        f"runs:{self._repo_owner}/{self._repo_name}",
                        runs,
                        ttl=300,
                    )
                else:
                    runs = cached_runs

            except (NotFoundError, RateLimitError, AuthError, GithubAPIError) as exc:
                cached = cache.get(cache_key)
                if cached:
                    self._offline_mode = True
                    data = cached
                    contributors = (
                        cache.get(
                            f"contrib:{self._repo_owner}/{self._repo_name}"
                        )
                        or []
                    )
                    runs = (
                        cache.get(
                            f"runs:{self._repo_owner}/{self._repo_name}"
                        )
                        or []
                    )
                else:
                    self.call_from_thread(self._show_error, str(exc))
                    return

            except httpx.HTTPError as exc:
                self.call_from_thread(self._show_error, f"Network error: {exc}")
                return

            except Exception as exc:
                self.call_from_thread(self._show_error, f"Unexpected error: {exc}")
                return

            repo = data.get("repository") if data else None
            if repo is None:
                self.call_from_thread(
                    self._show_error,
                    f"Repository {self._repo_owner}/{self._repo_name} not found "
                    f"or inaccessible",
                )
                return

            self._ref = repo.get("defaultBranchRef", {}).get("name") or "HEAD"

            self.call_from_thread(self._update_header, repo)
            self.call_from_thread(self._populate_tree, repo)
            self.call_from_thread(self._populate_languages, repo)
            self.call_from_thread(self._populate_contributors, contributors or [])
            self.call_from_thread(self._populate_readme, repo)
            self.call_from_thread(self._populate_issues, data)
            self.call_from_thread(self._populate_actions, runs)

        except Exception as exc:
            self.call_from_thread(self._show_error, f"Fatal error in _load_data: {exc}")

    # ------------------------------------------------------------------
    #  Error display
    # ------------------------------------------------------------------

    async def _show_error(self, message: str) -> None:
        try:
            header = self.query_one("#repo-header")
            await header.remove_children()
            await header.mount(Static(f"Error: {message}", id="header-error"))
        except Exception:
            pass

        try:
            container = self.query_one("#main-container")
            await container.remove_children()
            await container.mount(
                Static(
                    f"\n  Failed to load repository.\n\n  {message}\n\n"
                    f"  Check the URL and your network connection, then try again.",
                    id="error-message",
                )
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    #  Header
    # ------------------------------------------------------------------

    async def _update_header(self, repo: dict[str, Any]) -> None:
        prefix = "[Offline Mode] " if self._offline_mode else ""
        owner = repo.get("owner", {}).get("login", "?")
        name = repo.get("name", "?")
        stars = repo.get("stargazerCount", 0)
        forks = repo.get("forkCount", 0)
        watchers = repo.get("watchers", {}).get("totalCount", 0)

        header = self.query_one("#repo-header")
        await header.remove_children()
        await header.mount(
            Static(f"{prefix}{owner}/{name}", id="header-repo-name"),
            Static(f"Stars: {stars}", id="header-stars"),
            Static(f"Forks: {forks}", id="header-forks"),
            Static(f"Watchers: {watchers}", id="header-watchers"),
        )

    # ------------------------------------------------------------------
    #  File tree
    # ------------------------------------------------------------------

    def _populate_tree(self, repo: dict[str, Any]) -> None:
        tree: Tree[dict] = self.query_one("#file-tree")
        root = tree.root
        root.label = f"{self._repo_owner}/{self._repo_name}"
        root.expand()

        tree_obj = repo.get("object")
        if tree_obj and isinstance(tree_obj, dict):
            entries = tree_obj.get("entries", [])
            self._add_tree_entries(root, entries, "")

    def _add_tree_entries(
        self,
        parent: TreeNode[dict],
        entries: list[dict[str, Any]],
        base_path: str,
    ) -> None:
        for entry in entries:
            name: str = entry.get("name", "?")
            path = f"{base_path}/{name}" if base_path else name
            entry_type: str = entry.get("type", "blob")

            node = parent.add(
                name,
                data={
                    "type": entry_type,
                    "path": path,
                    "oid": entry.get("oid", ""),
                },
            )
            if entry_type == "tree":
                node.allow_expand = True

    def on_tree_node_expanded(self, event: Tree.NodeExpanded[dict]) -> None:
        node = event.node
        data = node.data or {}
        if data.get("type") != "tree" or node.children:
            return

        self.load_subdir_entries(node, data.get("path", ""))

    @work(thread=True)
    def load_subdir_entries(self, node: TreeNode[dict], path: str) -> None:
        token = get_pat()
        client = RepoAPIClient(token=token)
        try:
            entries = client.get_subdir_entries(
                self._repo_owner, self._repo_name, self._ref, path
            )
            self.call_from_thread(self._add_tree_entries, node, entries, path)
        except Exception:
            self.call_from_thread(node.add, "[failed to load]", {"type": "error"})

    def on_tree_node_selected(self, event: Tree.NodeSelected[dict]) -> None:
        node = event.node
        data = node.data or {}
        if data.get("type") != "blob":
            return

        path: str = data.get("path", "")
        ext = Path(path).suffix.lower()

        if ext in BINARY_EXTENSIONS:
            self.query_one("#code-viewer").update(
                f"Cannot display binary file: {path}"
            )
            self.query_one("#content-tabs").active = "tab-code"
            return

        self.query_one("#code-viewer").update(f"Loading {path}...")
        self.query_one("#content-tabs").active = "tab-code"
        self.load_file_content(path, ext)

    @work(exclusive=True, thread=True)
    def load_file_content(self, path: str, ext: str) -> None:
        token = get_pat()
        client = RepoAPIClient(token=token)
        expression = f"{self._ref}:{path}"
        try:
            blob = client.get_file_content(
                self._repo_owner, self._repo_name, expression
            )
        except Exception as exc:
            self.call_from_thread(self._update_code_viewer, f"Error loading file: {exc}")
            return

        if blob and blob.get("text") and not blob.get("isBinary"):
            code = blob["text"]
            lang = EXTENSION_LANG.get(ext, "text")
            try:
                syntax = Syntax(
                    code, lang, theme="monokai", line_numbers=True, word_wrap=False
                )
            except Exception:
                syntax = Syntax(code, "text", theme="monokai", line_numbers=True)
            self.call_from_thread(self._update_code_viewer, syntax)
        elif blob and blob.get("isBinary"):
            self.call_from_thread(self._update_code_viewer, "Binary file cannot be displayed.")
        else:
            self.call_from_thread(self._update_code_viewer, f"[empty or unavailable]: {path}")

    def _update_code_viewer(self, content: Any) -> None:
        self.query_one("#code-viewer").update(content)

    # ------------------------------------------------------------------
    #  README
    # ------------------------------------------------------------------

    async def _populate_readme(self, repo: dict[str, Any]) -> None:
        readme = repo.get("readme")
        widget = self.query_one("#readme-viewer")
        if readme and isinstance(readme, dict) and readme.get("text"):
            try:
                md = Markdown(readme["text"], id="readme-viewer")
                tab = self.query_one("#tab-readme")
                try:
                    await widget.remove()
                except Exception:
                    pass
                await tab.mount(md)
            except Exception:
                widget.update("README rendering failed")
        else:
            widget.update("No README found")

    # ------------------------------------------------------------------
    #  Languages
    # ------------------------------------------------------------------

    def _populate_languages(self, repo: dict[str, Any]) -> None:
        languages = repo.get("languages", {})
        edges = languages.get("edges", []) if isinstance(languages, dict) else []
        total = languages.get("totalSize", 1) if isinstance(languages, dict) else 1
        if total == 0:
            total = 1

        if edges:
            lines = []
            for edge in edges:
                node = edge.get("node", {})
                name = node.get("name", "?")
                size = edge.get("size", 0)
                pct = (size / total) * 100
                lines.append(f"{name:20s} {pct:5.1f}%")
            self.query_one("#languages-content").update("\n".join(lines))
        else:
            self.query_one("#languages-content").update("No language data")

    # ------------------------------------------------------------------
    #  Contributors
    # ------------------------------------------------------------------

    def _populate_contributors(self, contributors: list[dict[str, Any]]) -> None:
        if contributors:
            lines = [
                f"{c.get('login', '?'):20s} ({c.get('contributions', 0)} commits)"
                for c in contributors[:8]
            ]
            self.query_one("#contributors-content").update("\n".join(lines))
        else:
            self.query_one("#contributors-content").update("No contributor data")

    # ------------------------------------------------------------------
    #  Issues
    # ------------------------------------------------------------------

    async def _populate_issues(self, data: Optional[dict[str, Any]]) -> None:
        issues_list = self.query_one("#issues-list")
        issues = (
            (data.get("repository") or {}).get("issues", {}).get("nodes", [])
            if data
            else []
        )
        if not issues:
            await issues_list.mount(Static("No open issues"))
            return

        for issue in issues:
            tag = "open" if issue.get("state") == "OPEN" else "closed"
            title = issue.get("title", "?")
            number = issue.get("number", "?")
            author = (issue.get("author") or {}).get("login", "?")
            await issues_list.mount(
                Horizontal(
                    Label(tag, classes=f"issue-badge issue-{tag}"),
                    Label(f"{title} (#{number})", classes="issue-title-label"),
                    Label(author, classes="issue-author"),
                )
            )

    # ------------------------------------------------------------------
    #  Actions / Workflow runs
    # ------------------------------------------------------------------

    async def _populate_actions(self, runs: list[dict[str, Any]]) -> None:
        actions_view = self.query_one("#actions-view")
        if not isinstance(runs, list):
            runs = []
        if not runs:
            await actions_view.mount(Static("No workflow runs"))
            return

        for run in runs:
            workflow = run.get("name", "?")
            branch = run.get("head_branch", "?")
            conclusion = run.get("conclusion") or "in_progress"
            passed = conclusion == "success"
            status_str = (
                "PASS"
                if passed
                else conclusion.replace("_", " ").title()
                if conclusion
                else "In Progress"
            )
            status_class = "action-pass" if passed else "action-fail"

            await actions_view.mount(
                Horizontal(
                    Label(f"[{workflow}]", classes="action-label"),
                    Label(branch, classes="action-branch"),
                    Label(status_str, classes=f"action-status {status_class}"),
                )
            )
