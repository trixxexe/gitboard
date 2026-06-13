from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LanguageStat:
    name: str
    color: Optional[str]
    size: int
    percentage: float


@dataclass
class TreeEntry:
    name: str
    type: str
    oid: str
    mode: int


@dataclass
class RepoInfo:
    owner: str
    name: str
    description: Optional[str]
    stargazer_count: int
    fork_count: int
    watcher_count: int
    default_branch: str
    primary_language: Optional[str]
    languages: list[LanguageStat] = field(default_factory=list)
    root_entries: list[TreeEntry] = field(default_factory=list)
    readme_text: Optional[str] = None
