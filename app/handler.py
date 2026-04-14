import json
import hashlib
import hmac
import os
import logging

from github_client import GitHubClient
from log_parser import LogParser
from prompt_builder import PromptBuilder
from llm_client import LLMClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload_body: str, signature_header: str) -> bool:
    """Verify that the webhook payload was sent by GitHub."""
    if not signature_header:
        return False

    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        payload_body.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    received = signature_header.replace("sha256=", "")
    return hmac.compare_digest(expected, received)


def handler(event, context):
    """Lambda entry point — receives GitHub webhook, orchestrates the debugger."""
    logger.info("Received webhook event")

    # Step 1: Extract headers and body
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    body_str = event.get("body", "")

    # Step 2: Verify webhook signature
    signature = headers.get("x-hub-signature-256", "")
    if not verify_signature(body_str, signature):
        logger.warning("Invalid webhook signature")
        return {"statusCode": 401, "body": json.dumps({"error": "Invalid signature"})}

    # Step 3: Parse the webhook payload
    payload = json.loads(body_str)
    action = payload.get("action")
    workflow_run = payload.get("workflow_run", {})
    conclusion = workflow_run.get("conclusion")

    # Step 4: Only process failed workflow runs
    if action != "completed" or conclusion != "failure":
        logger.info(f"Skipping — action: {action}, conclusion: {conclusion}")
        return {"statusCode": 200, "body": json.dumps({"message": "Skipped — not a failure"})}

    # Step 5: Extract details from the payload
    repo_full_name = payload["repository"]["full_name"]
    run_id = workflow_run["id"]
    head_sha = workflow_run["head_sha"]
    head_branch = workflow_run["head_branch"]

    logger.info(f"Processing failure — repo: {repo_full_name}, run: {run_id}")

    # Step 6: Fetch failure logs and PR diff from GitHub
    gh = GitHubClient()
    logs = gh.get_workflow_logs(repo_full_name, run_id)
    pr_number = gh.get_pr_for_branch(repo_full_name, head_branch)

    diff = ""
    if pr_number:
        diff = gh.get_pr_diff(repo_full_name, pr_number)

    # Step 7: Clean and parse the logs
    parser = LogParser()
    parsed_logs = parser.parse(logs)

    # Step 8: Build the prompt
    builder = PromptBuilder()
    prompt = builder.build(
        logs=parsed_logs,
        diff=diff,
        repo=repo_full_name,
        branch=head_branch
    )

    # Step 9: Call the LLM
    llm = LLMClient()
    diagnosis = llm.analyze(prompt)

    # Step 10: Post the diagnosis as a PR comment
    if pr_number:
        gh.post_comment(repo_full_name, pr_number, diagnosis)
        logger.info(f"Posted diagnosis on PR #{pr_number}")
    else:
        logger.warning("No PR found for this branch — diagnosis not posted")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Diagnosis complete",
            "pr": pr_number,
            "run_id": run_id
        })
    }