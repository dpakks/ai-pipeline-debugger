import os
import json
import logging
import boto3

logger = logging.getLogger()

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")


class LLMClient:
    """Talks to AWS Bedrock. This is the only file that knows which LLM we're using."""

    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    def analyze(self, prompt: dict) -> str:
        """Send the prompt to Bedrock and return the diagnosis."""
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "system": prompt["system"],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt["user"]
                    }
                ]
            })

            response = self.client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body
            )

            result = json.loads(response["body"].read())
            diagnosis = result["content"][0]["text"]

            return self._format_comment(diagnosis)

        except Exception as e:
            logger.error(f"Bedrock call failed: {str(e)}")
            return self._format_error(str(e))

    def _format_comment(self, diagnosis: str) -> str:
        """Wrap the diagnosis in a clean GitHub comment format."""
        return (
            "## 🔍 CI/CD Pipeline Failure Diagnosis\n\n"
            f"{diagnosis}\n\n"
            "---\n"
            "*Automated analysis by [CI/CD Debugger](https://github.com) — "
            "powered by AWS Bedrock*"
        )

    def _format_error(self, error: str) -> str:
        """Return a helpful comment even when the LLM call fails."""
        return (
            "## ⚠️ CI/CD Debugger — Analysis Failed\n\n"
            "The automated analysis could not be completed.\n\n"
            f"**Error:** `{error}`\n\n"
            "Please review the workflow logs manually.\n\n"
            "---\n"
            "*Automated analysis by [CI/CD Debugger](https://github.com) — "
            "powered by AWS Bedrock*"
        )
