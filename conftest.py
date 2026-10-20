"""pytest path setup: the AI session tools (code_edit, code_search) live in
AI_tools/, not the repo root (session 41, addendum 38 ruling 3)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI_tools"))

from argparse import ArgumentParser, Namespace
from unittest.mock import MagicMock

import pytest

mock_process = MagicMock()
mock_process.close.return_value = True


@pytest.fixture
def mock_process():
    """Mock process for testing sigint shutdown."""
    return mock_process


@pytest.fixture
def mock_args():
    """Mock argparse Namespace object."""

    return Namespace()


@pytest.fixture
def mock_parser():
    """Mock ArgumentParser for testing."""
    return ArgumentParser()


@pytest.fixture
def mock_convert_quant():
    """Mock convert_quant for testing."""

    class MockQuant:
        @staticmethod
        def create(
            fam: str, famdir: str, rung: str, plan: str = "", dry_run: bool = False
        ) -> str | None:
            return f"fake_quant_{fam}-{rung}.gguf"

    return MockQuant()


@pytest.fixture
def mock_git_ops():
    """Mock git_ops for testing."""

    class MockGitOps:
        @staticmethod
        def pull_rebase(autostash: bool = True) -> tuple[int, str, str]:
            return (0, "main", "HEAD")

        @staticmethod
        def add(paths: list[str], force: bool = True) -> tuple[int, str]:
            return (0, "main")

        @staticmethod
        def staged_changes_exist() -> bool:
            return True

        @staticmethod
        def commit(message: str) -> tuple[int, str]:
            return (0, "main")

        @staticmethod
        def push() -> tuple[int, str]:
            return (0, "main")

    return MockGitOps()
