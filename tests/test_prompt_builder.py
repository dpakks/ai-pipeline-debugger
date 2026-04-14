import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from prompt_builder import PromptBuilder


builder = PromptBuilder()


class TestBuildPrompt:
    def test_returns_system_and_user_keys(self):
        result = builder.build(
            logs="Error: build failed",
            diff="+ import broken",
            repo="myorg/myrepo",
            branch="feature/test"
        )
        assert "system" in result
        assert "user" in result

    def test_system_prompt_sets_devops_persona(self):
        result = builder.build(
            logs="error",
            diff="",
            repo="org/repo",
            branch="main"
        )
        assert "DevOps" in result["system"]
        assert "CI/CD" in result["system"]

    def test_user_prompt_contains_logs(self):
        result = builder.build(
            logs="ModuleNotFoundError: No module named 'boto3'",
            diff="",
            repo="org/repo",
            branch="main"
        )
        assert "ModuleNotFoundError" in result["user"]

    def test_user_prompt_contains_repo_and_branch(self):
        result = builder.build(
            logs="error",
            diff="",
            repo="myorg/myrepo",
            branch="feature/cool-thing"
        )
        assert "myorg/myrepo" in result["user"]
        assert "feature/cool-thing" in result["user"]

    def test_user_prompt_includes_diff_when_provided(self):
        result = builder.build(
            logs="error",
            diff="+ import nonexistent_module",
            repo="org/repo",
            branch="main"
        )
        assert "nonexistent_module" in result["user"]
        assert "Code Changes" in result["user"]

    def test_user_prompt_excludes_diff_section_when_empty(self):
        result = builder.build(
            logs="error",
            diff="",
            repo="org/repo",
            branch="main"
        )
        assert "Code Changes" not in result["user"]

    def test_user_prompt_contains_response_instructions(self):
        result = builder.build(
            logs="error",
            diff="",
            repo="org/repo",
            branch="main"
        )
        assert "Root Cause" in result["user"]
        assert "Fix" in result["user"]
        assert "Prevention" in result["user"]


class TestTrimDiff:
    def test_short_diff_not_trimmed(self):
        result = builder.build(
            logs="error",
            diff="+ one line change",
            repo="org/repo",
            branch="main"
        )
        assert "truncated" not in result["user"]

    def test_long_diff_is_trimmed(self):
        long_diff = "+ added line\n" * 5000
        result = builder.build(
            logs="error",
            diff=long_diff,
            repo="org/repo",
            branch="main"
        )
        assert "truncated" in result["user"]