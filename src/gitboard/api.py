import json
import logging
from typing import Any, Optional

import httpx

from gitboard.config import GRAPHQL_URL, REST_API_URL, USER_AGENT

logger = logging.getLogger(__name__)


class GithubAPIError(Exception):
    pass


class NotFoundError(GithubAPIError):
    pass


class RateLimitError(GithubAPIError):
    pass


class AuthError(GithubAPIError):
    pass


_REPO_QUERY = """
query RepoData($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    owner { login }
    description
    stargazerCount
    forkCount
    watchers { totalCount }
    defaultBranchRef { name }
    primaryLanguage { name color }
    languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
      totalSize
      edges {
        size
        node { name color }
      }
    }
    object(expression: "HEAD:") {
      ... on Tree {
        entries {
          name
          type
          oid
          mode
        }
      }
    }
    readme: object(expression: "HEAD:README.md") {
      ... on Blob {
        text
        isTruncated
      }
    }
    issues(first: 10, states: OPEN, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes {
        number
        title
        state
        createdAt
        author { login }
      }
    }
  }
  rateLimit {
    limit
    cost
    remaining
    resetAt
  }
}
"""

_SUBDIR_QUERY = """
query SubdirEntries($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) {
      ... on Tree {
        entries {
          name
          type
          oid
          mode
        }
      }
    }
  }
}
"""

_FILE_CONTENT_QUERY = """
query FileContent($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) {
      ... on Blob {
        text
        isTruncated
        byteSize
        isBinary
      }
    }
  }
}
"""


class RepoAPIClient:
    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github.v4+json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def _execute(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
            )
        except httpx.TimeoutException:
            raise GithubAPIError(
                "Request timed out after 30s. Check your network or try again."
            )
        except httpx.NetworkError as exc:
            raise GithubAPIError(f"Network error: {exc}")

        if response.status_code == 200:
            try:
                body = response.json()
            except json.JSONDecodeError:
                raise GithubAPIError(
                    f"Invalid JSON from GitHub API: {response.text[:300]}"
                )

            errors = body.get("errors")
            if errors:
                messages = [
                    e.get("message", str(e))
                    for e in errors
                    if isinstance(e, dict)
                ]
                msg = "; ".join(messages) if messages else "Unknown GraphQL error"
                raise GithubAPIError(msg)

            if "data" not in body:
                raise GithubAPIError(
                    "GitHub API response missing 'data' field"
                )

            return body["data"]

        if response.status_code == 401:
            raise AuthError("Invalid or expired GitHub token")
        if response.status_code == 403:
            raise RateLimitError(
                "API rate limit exceeded. Authenticate with a PAT for higher limits."
            )
        if response.status_code == 404:
            raise NotFoundError("Repository not found")

        raise GithubAPIError(
            f"HTTP {response.status_code}: {response.text[:500]}"
        )

    def get_repo_data(self, owner: str, name: str) -> dict[str, Any]:
        data = self._execute(_REPO_QUERY, {"owner": owner, "name": name})
        repo = data.get("repository")
        if repo is None:
            raise NotFoundError(
                f"Repository {owner}/{name} not found or is private"
            )
        return data

    def get_subdir_entries(
        self, owner: str, name: str, ref: str, path: str
    ) -> list[dict[str, Any]]:
        expression = f"{ref}:{path}" if path else ref
        data = self._execute(
            _SUBDIR_QUERY,
            {"owner": owner, "name": name, "expression": expression},
        )
        obj = data.get("repository", {}).get("object")
        if obj and isinstance(obj, dict):
            return obj.get("entries", [])
        return []

    def get_file_content(
        self, owner: str, name: str, expression: str
    ) -> Optional[dict[str, Any]]:
        data = self._execute(
            _FILE_CONTENT_QUERY,
            {"owner": owner, "name": name, "expression": expression},
        )
        return data.get("repository", {}).get("object")

    def get_contributors(
        self, owner: str, name: str, per_page: int = 5
    ) -> list[dict[str, Any]]:
        url = (
            f"{REST_API_URL}/repos/{owner}/{name}/contributors"
            f"?per_page={per_page}&anon=false"
        )
        try:
            response = self._client.get(url)
            if response.status_code == 200:
                return response.json()
            logger.debug("contributors fetch returned %d", response.status_code)
        except httpx.HTTPError as exc:
            logger.debug("contributors fetch failed: %s", exc)
        return []

    def get_workflow_runs(
        self, owner: str, name: str, per_page: int = 10
    ) -> list[dict[str, Any]]:
        url = f"{REST_API_URL}/repos/{owner}/{name}/actions/runs?per_page={per_page}"
        try:
            response = self._client.get(url)
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logger.debug("workflow runs: invalid JSON")
                    return []
                if not isinstance(data, dict):
                    return []
                return data.get("workflow_runs", [])
            logger.debug("workflow runs fetch returned %d", response.status_code)
        except Exception as exc:
            logger.debug("workflow runs fetch failed: %s", exc)
        return []

    def get_default_branch(self, owner: str, name: str) -> str:
        url = f"{REST_API_URL}/repos/{owner}/{name}"
        try:
            response = self._client.get(url)
            if response.status_code == 200:
                return response.json().get("default_branch", "HEAD")
        except httpx.HTTPError as exc:
            logger.debug("default branch fetch failed: %s", exc)
        return "HEAD"
