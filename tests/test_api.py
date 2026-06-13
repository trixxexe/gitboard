
import httpx
import pytest

from gitboard.api import (
    AuthError,
    GithubAPIError,
    NotFoundError,
    RateLimitError,
    RepoAPIClient,
)


def _mock_response(content: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status_code, json=content)


def test_get_repo_data_success(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response(
        {
            "data": {
                "repository": {
                    "name": "test-repo",
                    "owner": {"login": "test-owner"},
                    "description": "A test repo",
                    "stargazerCount": 42,
                    "forkCount": 7,
                    "watchers": {"totalCount": 3},
                    "defaultBranchRef": {"name": "main"},
                    "primaryLanguage": {"name": "Python", "color": "#3572A5"},
                    "languages": {
                        "totalSize": 1000,
                        "edges": [
                            {
                                "size": 800,
                                "node": {"name": "Python", "color": "#3572A5"},
                            },
                            {
                                "size": 200,
                                "node": {"name": "HTML", "color": "#e34c26"},
                            },
                        ],
                    },
                    "object": {
                        "entries": [
                            {"name": "src", "type": "tree", "oid": "abc", "mode": 40755},
                            {"name": "README.md", "type": "blob", "oid": "def", "mode": 100644},
                        ]
                    },
                    "readme": {"text": "# Hello", "isTruncated": False},
                },
                "rateLimit": {"limit": 5000, "cost": 1, "remaining": 4999, "resetAt": "2026-01-01T00:00:00Z"},
            }
        }
    )

    client = RepoAPIClient(token="ghp_test")
    data = client.get_repo_data("test-owner", "test-repo")
    client.close()

    repo = data["repository"]
    assert repo["name"] == "test-repo"
    assert repo["owner"]["login"] == "test-owner"
    assert repo["stargazerCount"] == 42
    assert len(repo["object"]["entries"]) == 2
    assert repo["readme"]["text"] == "# Hello"
    assert data["rateLimit"]["remaining"] == 4999


def test_get_repo_data_without_token(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response(
        {
            "data": {
                "repository": {
                    "name": "public-repo",
                    "owner": {"login": "public-user"},
                    "description": None,
                    "stargazerCount": 0,
                    "forkCount": 0,
                    "watchers": {"totalCount": 1},
                    "defaultBranchRef": {"name": "master"},
                    "primaryLanguage": None,
                    "languages": {"totalSize": 0, "edges": []},
                    "object": {"entries": []},
                    "readme": None,
                },
                "rateLimit": {"limit": 60, "cost": 1, "remaining": 59, "resetAt": ""},
            }
        }
    )

    client = RepoAPIClient()
    data = client.get_repo_data("public-user", "public-repo")
    client.close()

    assert data["repository"]["stargazerCount"] == 0
    assert data["repository"]["readme"] is None


def test_raises_not_found(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response({"message": "Not Found"}, status_code=404)

    client = RepoAPIClient()
    with pytest.raises(NotFoundError, match="not found"):
        client.get_repo_data("unknown", "missing")
    client.close()


def test_raises_rate_limit(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response({"message": "rate limit"}, status_code=403)

    client = RepoAPIClient()
    with pytest.raises(RateLimitError, match="rate limit"):
        client.get_repo_data("owner", "repo")
    client.close()


def test_raises_auth_error(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response({"message": "bad creds"}, status_code=401)

    client = RepoAPIClient(token="ghp_bad")
    with pytest.raises(AuthError, match="token"):
        client.get_repo_data("owner", "repo")
    client.close()


def test_raises_on_graphql_errors(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response(
        {"errors": [{"message": "Field 'name' doesn't exist"}]}
    )

    client = RepoAPIClient()
    with pytest.raises(GithubAPIError, match="doesn't exist"):
        client.get_repo_data("owner", "repo")
    client.close()


def test_raises_on_unknown_status(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response({"message": "teapot"}, status_code=418)

    client = RepoAPIClient()
    with pytest.raises(GithubAPIError, match="418"):
        client.get_repo_data("owner", "repo")
    client.close()


def test_get_subdir_entries(mocker):
    mock_post = mocker.patch.object(httpx.Client, "post")
    mock_post.return_value = _mock_response(
        {
            "data": {
                "repository": {
                    "object": {
                        "entries": [
                            {"name": "main.py", "type": "blob", "oid": "x", "mode": 100644},
                            {"name": "utils.py", "type": "blob", "oid": "y", "mode": 100644},
                        ]
                    }
                }
            }
        }
    )

    client = RepoAPIClient()
    entries = client.get_subdir_entries("user", "repo", "main", "src")
    client.close()

    assert len(entries) == 2
    assert entries[0]["name"] == "main.py"
