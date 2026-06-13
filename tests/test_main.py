import pytest

from gitboard.main import parse_repo_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo.git", ("owner", "repo")),
        ("https://github.com/owner/repo/", ("owner", "repo")),
        ("http://github.com/owner/repo", ("owner", "repo")),
        ("https://github.com/owner/repo/issues", ("owner", "repo")),
        ("git@github.com:owner/repo.git", ("owner", "repo")),
        ("git@github.com:owner/repo", ("owner", "repo")),
        ("owner/repo", ("owner", "repo")),
        ("github.com/owner/repo", ("owner", "repo")),
    ],
)
def test_parse_repo_url_valid(url, expected):
    assert parse_repo_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "https://gitlab.com/owner/repo",
    ],
)
def test_parse_repo_url_invalid(url):
    with pytest.raises(ValueError):
        parse_repo_url(url)
