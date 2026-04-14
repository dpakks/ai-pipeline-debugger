import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from log_parser import LogParser


parser = LogParser()


class TestRemoveNoise:
    def test_strips_ansi_color_codes(self):
        raw = "\x1b[31mError: something failed\x1b[0m"
        result = parser.parse(raw)
        assert "\x1b[" not in result
        assert "Error: something failed" in result

    def test_strips_iso_timestamps(self):
        raw = "2024-09-15T14:23:01.123Z Error: build failed"
        result = parser.parse(raw)
        assert "2024-09-15T" not in result
        assert "Error: build failed" in result

    def test_strips_github_debug_lines(self):
        raw = (
            "##[debug] Evaluating condition\n"
            "##[group] Run npm install\n"
            "Error: module not found\n"
            "##[endgroup]"
        )
        result = parser.parse(raw)
        assert "##[debug]" not in result
        assert "##[group]" not in result
        assert "##[endgroup]" not in result
        assert "module not found" in result

    def test_removes_blank_lines(self):
        raw = "line one\n\n\n\nError: failure\n\n\n"
        result = parser.parse(raw)
        assert "\n\n\n" not in result


class TestExtractRelevantSections:
    def test_extracts_lines_around_errors(self):
        lines = [
            "Step 1: Installing dependencies",
            "Step 2: Running build",
            "Step 3: Compiling source",
            "Error: Cannot find module 'express'",
            "at Object.<anonymous> (/app/index.js:1:15)",
            "Step 4: Cleanup",
            "Step 5: Done",
        ]
        raw = "\n".join(lines)
        result = parser.parse(raw)
        assert "Cannot find module" in result
        assert "Compiling source" in result  # context before
        assert "Object.<anonymous>" in result  # context after

    def test_separates_distant_error_sections(self):
        lines = ["line"] * 20
        lines[3] = "Error: first failure"
        lines[15] = "Error: second failure"
        raw = "\n".join(lines)
        result = parser.parse(raw)
        assert "first failure" in result
        assert "second failure" in result
        assert "---" in result  # separator between sections

    def test_returns_cleaned_logs_when_no_errors_found(self):
        raw = "Step 1: success\nStep 2: success\nStep 3: all good"
        result = parser.parse(raw)
        assert "success" in result


class TestSmartTruncate:
    def test_truncates_long_logs_keeping_start_and_end(self):
        raw = "Error: start\n" + ("x" * 20000) + "\nError: end"
        result = parser.parse(raw)
        assert len(result) <= 15500  # MAX_LOG_LENGTH + separator text
        assert "start" in result
        assert "end" in result
        assert "truncated" in result

    def test_short_logs_not_truncated(self):
        raw = "Error: simple failure"
        result = parser.parse(raw)
        assert "truncated" not in result


class TestEmptyInput:
    def test_empty_string_returns_no_logs(self):
        assert parser.parse("") == "No logs available."

    def test_none_like_empty(self):
        assert parser.parse("") == "No logs available."