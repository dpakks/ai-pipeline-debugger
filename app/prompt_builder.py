class PromptBuilder:
    """Constructs structured prompts for the LLM to analyze CI/CD failures."""

    SYSTEM_PROMPT = (
        "You are a senior DevOps engineer who specializes in diagnosing CI/CD pipeline failures. "
        "You are precise, concise, and always provide actionable fixes. "
        "When analyzing logs, you focus on root causes, not symptoms. "
        "You format your responses in Markdown suitable for a GitHub PR comment."
    )

    def build(self, logs: str, diff: str, repo: str, branch: str) -> dict:
        """Build the full prompt with all available context."""
        sections = [
            f"## CI/CD Pipeline Failure Analysis Request",
            f"**Repository:** {repo}",
            f"**Branch:** {branch}",
            "",
            "### Failure Logs",
            "```",
            logs,
            "```",
        ]

        if diff:
            sections.extend([
                "",
                "### Code Changes (PR Diff)",
                "```diff",
                self._trim_diff(diff),
                "```",
            ])

        sections.extend([
            "",
            "### Instructions",
            "Analyze the above CI/CD failure and respond with:",
            "1. **Root Cause** — What exactly caused the failure (one or two sentences)",
            "2. **Explanation** — Why this caused the pipeline to break",
            "3. **Fix** — The exact steps or code changes needed to resolve it",
            "4. **Prevention** — How to prevent this from happening again",
            "",
            "Keep your response concise and actionable. No fluff.",
        ])

        return {
            "system": self.SYSTEM_PROMPT,
            "user": "\n".join(sections)
        }

    def _trim_diff(self, diff: str, max_length: int = 5000) -> str:
        """Trim large diffs to stay within token limits."""
        if len(diff) <= max_length:
            return diff

        return diff[:max_length] + f"\n\n... [diff truncated — {len(diff) - max_length} characters removed]"