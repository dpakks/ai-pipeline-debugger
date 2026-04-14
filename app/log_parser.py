import re
import logging

logger = logging.getLogger()

# Maximum characters to send to LLM — keeps cost and latency down
MAX_LOG_LENGTH = 15000


class LogParser:
    """Cleans and structures raw CI/CD logs before sending to the LLM."""

    # Patterns that indicate an error or failure
    ERROR_PATTERNS = [
        re.compile(r"error", re.IGNORECASE),
        re.compile(r"failed", re.IGNORECASE),
        re.compile(r"exception", re.IGNORECASE),
        re.compile(r"traceback", re.IGNORECASE),
        re.compile(r"exit code \d+", re.IGNORECASE),
        re.compile(r"command not found", re.IGNORECASE),
        re.compile(r"permission denied", re.IGNORECASE),
        re.compile(r"module not found", re.IGNORECASE),
        re.compile(r"syntax error", re.IGNORECASE),
        re.compile(r"timed? ?out", re.IGNORECASE),
    ]

    # Noise patterns to strip out
    NOISE_PATTERNS = [
        re.compile(r"\x1b\[[0-9;]*m"),           # ANSI color codes
        re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*"),  # ISO timestamps
        re.compile(r"^##\[debug\].*$", re.MULTILINE),    # GitHub debug lines
        re.compile(r"^##\[group\].*$", re.MULTILINE),    # GitHub group markers
        re.compile(r"^##\[endgroup\].*$", re.MULTILINE), # GitHub endgroup markers
    ]

    def parse(self, raw_logs: str) -> str:
        """Clean raw logs and extract the most relevant sections."""
        if not raw_logs:
            return "No logs available."

        # Step 1: Remove noise
        cleaned = self._remove_noise(raw_logs)

        # Step 2: Extract error-relevant sections
        relevant = self._extract_relevant_sections(cleaned)

        # Step 3: Truncate if too long
        result = relevant if relevant else cleaned
        if len(result) > MAX_LOG_LENGTH:
            result = self._smart_truncate(result)

        logger.info(f"Parsed logs: {len(raw_logs)} chars -> {len(result)} chars")
        return result

    def _remove_noise(self, logs: str) -> str:
        """Strip ANSI codes, timestamps, and GitHub debug lines."""
        for pattern in self.NOISE_PATTERNS:
            logs = pattern.sub("", logs)

        # Remove blank lines left behind after stripping
        lines = [line for line in logs.splitlines() if line.strip()]
        return "\n".join(lines)

    def _extract_relevant_sections(self, logs: str) -> str:
        """Pull out lines around errors with surrounding context."""
        lines = logs.splitlines()
        relevant_indices = set()

        for i, line in enumerate(lines):
            for pattern in self.ERROR_PATTERNS:
                if pattern.search(line):
                    # Grab 3 lines before and 3 lines after for context
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    relevant_indices.update(range(start, end))
                    break

        if not relevant_indices:
            return ""

        sorted_indices = sorted(relevant_indices)
        sections = []
        current_section = []

        for i, idx in enumerate(sorted_indices):
            current_section.append(lines[idx])
            # Add separator when there's a gap between relevant sections
            if i < len(sorted_indices) - 1 and sorted_indices[i + 1] - idx > 1:
                sections.append("\n".join(current_section))
                current_section = []

        if current_section:
            sections.append("\n".join(current_section))

        return "\n\n---\n\n".join(sections)

    def _smart_truncate(self, logs: str) -> str:
        """Truncate from the middle, keeping the beginning and end."""
        half = MAX_LOG_LENGTH // 2
        beginning = logs[:half]
        ending = logs[-half:]
        return f"{beginning}\n\n... [truncated {len(logs) - MAX_LOG_LENGTH} characters] ...\n\n{ending}"