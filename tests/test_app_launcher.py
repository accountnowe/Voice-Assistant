"""
Tests for the AppLauncher action module.
Uses mocked subprocess calls — does not actually launch apps.
Run with: pytest tests/test_app_launcher.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from actions.app_launcher import AppLauncher


class TestAppLauncher:

    def setup_method(self):
        self.launcher = AppLauncher()

    @patch("subprocess.run")
    def test_open_app_macos_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = self.launcher._open_macos("Spotify")
        assert success is True
        assert "Spotify" in msg

    @patch("subprocess.run")
    def test_open_app_macos_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="not found")
        success, msg = self.launcher._open_macos("FakeApp123")
        assert success is False
        assert "couldn't find" in msg.lower()

    @patch("subprocess.run")
    def test_close_app_macos_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        success, msg = self.launcher._close_macos("Spotify")
        assert success is True

    @patch("subprocess.run")
    def test_close_app_macos_not_running(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        success, msg = self.launcher._close_macos("FakeApp")
        assert success is False

    def test_is_running_returns_bool(self):
        """is_running should always return a bool, not raise."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = self.launcher.is_running("Finder")
        assert isinstance(result, bool)
