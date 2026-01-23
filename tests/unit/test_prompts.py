"""Unit tests for interactive prompts."""

from unittest.mock import patch

import pytest

from lazycommit.prompts import (
    edit_in_editor,
    get_editor,
    prompt_commit_message_review,
)


class TestGetEditor:
    """Test cases for get_editor function."""

    def test_gets_visual_env(self) -> None:
        """Test that VISUAL environment variable is preferred."""
        with patch.dict("os.environ", {"VISUAL": "code", "EDITOR": "vim"}):
            editor = get_editor()
            assert editor == "code"

    def test_gets_editor_env(self) -> None:
        """Test that EDITOR environment variable is used."""
        with patch.dict("os.environ", {"EDITOR": "vim"}, clear=True):
            editor = get_editor()
            assert editor == "vim"

    def test_falls_back_to_common_editors(self) -> None:
        """Test fallback to common editors."""
        with patch.dict("os.environ", {}, clear=True):
            # Mock which command to simulate nano being available
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                editor = get_editor()
                assert editor in ["nano", "vim", "vi", "emacs", "code", "subl"]


class TestEditInEditor:
    """Test cases for edit_in_editor function."""

    @pytest.mark.skip(reason="Complex file mocking - tested in integration tests")
    def test_edit_in_editor_success(self) -> None:
        """Test successful editing in editor."""
        # This is tested in integration tests since it involves
        # complex file operations and real editor invocation
        pass

    def test_edit_in_editor_cancelled(self) -> None:
        """Test editor exiting with non-zero status."""
        initial_text = "Original message"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            with patch("lazycommit.prompts.get_editor", return_value="false"):
                with patch("lazycommit.prompts.console"):
                    result = edit_in_editor(initial_text)

        assert result is None


class TestPromptCommitMessageReview:
    """Test cases for prompt_commit_message_review function."""

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.console")
    def test_user_accepts_message(self, mock_console, mock_prompt) -> None:
        """Test user accepting the message."""
        mock_prompt.return_value = "y"

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "yes"
        assert edited is None

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.console")
    def test_user_accepts_with_yes(self, mock_console, mock_prompt) -> None:
        """Test user accepting with 'yes'."""
        mock_prompt.return_value = "yes"

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "yes"
        assert edited is None

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.console")
    def test_user_rejects_message(self, mock_console, mock_prompt) -> None:
        """Test user rejecting the message."""
        mock_prompt.return_value = "n"

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "no"
        assert edited is None

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.console")
    def test_user_rejects_with_no(self, mock_console, mock_prompt) -> None:
        """Test user rejecting with 'no'."""
        mock_prompt.return_value = "no"

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "no"
        assert edited is None

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.edit_in_editor")
    @patch("lazycommit.prompts.console")
    def test_user_edits_message(self, mock_console, mock_edit, mock_prompt) -> None:
        """Test user editing the message."""
        mock_prompt.return_value = "e"
        mock_edit.return_value = "feat: edited feature"

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "edit"
        assert edited == "feat: edited feature"
        mock_edit.assert_called_once_with("feat: add feature")

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.edit_in_editor")
    @patch("lazycommit.prompts.console")
    def test_user_edits_with_edit(self, mock_console, mock_edit, mock_prompt) -> None:
        """Test user editing with 'edit'."""
        mock_prompt.return_value = "edit"
        mock_edit.return_value = "feat: edited feature"

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "edit"
        assert edited == "feat: edited feature"

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.edit_in_editor")
    @patch("lazycommit.prompts.console")
    def test_user_cancels_edit(self, mock_console, mock_edit, mock_prompt) -> None:
        """Test user cancelling the edit."""
        mock_prompt.return_value = "e"
        mock_edit.return_value = None  # Editor returned no changes

        action, edited = prompt_commit_message_review("feat: add feature")

        assert action == "no"
        assert edited is None

    @patch("lazycommit.prompts.Prompt.ask")
    @patch("lazycommit.prompts.console")
    def test_edit_disabled(self, mock_console, mock_prompt) -> None:
        """Test with editing disabled."""
        mock_prompt.return_value = "y"

        action, edited = prompt_commit_message_review(
            "feat: add feature", allow_edit=False
        )

        assert action == "yes"
        assert edited is None
