import json
import hashlib
import hmac
import pytest
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from handler import handler, verify_signature


# ------------------------------------------------
# Helper: build a fake webhook event
# ------------------------------------------------
def build_event(payload: dict, secret: str = "test-secret") -> dict:
    """Build a fake API Gateway event with a signed webhook body."""
    body = json.dumps(payload)
    signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return {
        "headers": {
            "x-hub-signature-256": signature,
            "content-type": "application/json"
        },
        "body": body
    }


FAILED_WORKFLOW_PAYLOAD = {
    "action": "completed",
    "workflow_run": {
        "id": 12345,
        "conclusion": "failure",
        "head_sha": "abc123",
        "head_branch": "feature/broken-thing"
    },
    "repository": {
        "full_name": "myorg/myrepo"
    }
}

SUCCESS_WORKFLOW_PAYLOAD = {
    "action": "completed",
    "workflow_run": {
        "id": 12345,
        "conclusion": "success",
        "head_sha": "abc123",
        "head_branch": "feature/working-thing"
    },
    "repository": {
        "full_name": "myorg/myrepo"
    }
}


# -----------------------------------------------
# Signature verification tests
# -----------------------------------------------
class TestVerifySignature:
    @patch("handler.WEBHOOK_SECRET", "test-secret")
    def test_valid_signature_passes(self):
        body = '{"test": "data"}'
        sig = "sha256=" + hmac.new(
            b"test-secret", body.encode(), hashlib.sha256
        ).hexdigest()
        assert verify_signature(body, sig) is True

    @patch("handler.WEBHOOK_SECRET", "test-secret")
    def test_invalid_signature_fails(self):
        assert verify_signature('{"test": "data"}', "sha256=invalid") is False

    @patch("handler.WEBHOOK_SECRET", "test-secret")
    def test_missing_signature_fails(self):
        assert verify_signature('{"test": "data"}', "") is False


# -----------------------------------------------
# Handler tests
# -----------------------------------------------
class TestHandler:
    @patch("handler.WEBHOOK_SECRET", "test-secret")
    def test_rejects_invalid_signature(self):
        event = {
            "headers": {"x-hub-signature-256": "sha256=wrong"},
            "body": '{"action": "completed"}'
        }
        result = handler(event, None)
        assert result["statusCode"] == 401

    @patch("handler.WEBHOOK_SECRET", "test-secret")
    def test_skips_successful_workflows(self):
        event = build_event(SUCCESS_WORKFLOW_PAYLOAD)
        result = handler(event, None)
        assert result["statusCode"] == 200
        assert "Skipped" in json.loads(result["body"])["message"]

    @patch("handler.WEBHOOK_SECRET", "test-secret")
    @patch("handler.GitHubClient")
    @patch("handler.LLMClient")
    def test_processes_failed_workflow(self, mock_llm_cls, mock_gh_cls):
        # Setup mocks
        mock_gh = MagicMock()
        mock_gh.get_workflow_logs.return_value = "Error: module not found"
        mock_gh.get_pr_for_branch.return_value = 42
        mock_gh.get_pr_diff.return_value = "+ import nonexistent"
        mock_gh_cls.return_value = mock_gh

        mock_llm = MagicMock()
        mock_llm.analyze.return_value = "## Diagnosis\nModule not found."
        mock_llm_cls.return_value = mock_llm

        event = build_event(FAILED_WORKFLOW_PAYLOAD)
        result = handler(event, None)

        assert result["statusCode"] == 200
        assert json.loads(result["body"])["pr"] == 42

        # Verify the full chain was called
        mock_gh.get_workflow_logs.assert_called_once_with("myorg/myrepo", 12345)
        mock_gh.get_pr_for_branch.assert_called_once_with("myorg/myrepo", "feature/broken-thing")
        mock_gh.get_pr_diff.assert_called_once_with("myorg/myrepo", 42)
        mock_llm.analyze.assert_called_once()
        mock_gh.post_comment.assert_called_once_with("myorg/myrepo", 42, "## Diagnosis\nModule not found.")

    @patch("handler.WEBHOOK_SECRET", "test-secret")
    @patch("handler.GitHubClient")
    @patch("handler.LLMClient")
    def test_handles_no_pr_found(self, mock_llm_cls, mock_gh_cls):
        mock_gh = MagicMock()
        mock_gh.get_workflow_logs.return_value = "Error: something broke"
        mock_gh.get_pr_for_branch.return_value = None
        mock_gh_cls.return_value = mock_gh

        mock_llm = MagicMock()
        mock_llm.analyze.return_value = "## Diagnosis\nSomething broke."
        mock_llm_cls.return_value = mock_llm

        event = build_event(FAILED_WORKFLOW_PAYLOAD)
        result = handler(event, None)

        assert result["statusCode"] == 200
        mock_gh.post_comment.assert_not_called()