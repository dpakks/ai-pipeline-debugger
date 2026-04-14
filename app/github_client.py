import os
import io
import zipfile
import logging
import requests

logger = logging.getLogger()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = "https://api.github.com"


class GitHubClient:
    """Handles all communication with the GitHub API."""

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    def get_workflow_logs(self, repo: str, run_id: int) -> str:
        """Download and extract logs from a failed workflow run."""
        url = f"{BASE_URL}/repos/{repo}/actions/runs/{run_id}/logs"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            logger.error(f"Failed to fetch logs: {response.status_code}")
            return ""

        # GitHub returns logs as a zip file
        logs = []
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for filename in zf.namelist():
                with zf.open(filename) as f:
                    content = f.read().decode("utf-8", errors="replace")
                    logs.append(f"=== {filename} ===\n{content}")

        return "\n\n".join(logs)

    def get_pr_for_branch(self, repo: str, branch: str) -> int | None:
        """Find the open PR number associated with a branch."""
        url = f"{BASE_URL}/repos/{repo}/pulls"
        params = {"head": f"{repo.split('/')[0]}:{branch}", "state": "open"}
        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code != 200:
            logger.error(f"Failed to fetch PRs: {response.status_code}")
            return None

        pulls = response.json()
        return pulls[0]["number"] if pulls else None

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the diff of a pull request."""
        url = f"{BASE_URL}/repos/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.diff"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            logger.error(f"Failed to fetch diff: {response.status_code}")
            return ""

        return response.text

    def post_comment(self, repo: str, pr_number: int, body: str) -> bool:
        """Post a comment on a pull request."""
        url = f"{BASE_URL}/repos/{repo}/issues/{pr_number}/comments"
        response = requests.post(
            url,
            headers=self.headers,
            json={"body": body}
        )

        if response.status_code != 201:
            logger.error(f"Failed to post comment: {response.status_code}")
            return False

        return True
