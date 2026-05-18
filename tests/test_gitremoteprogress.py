#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import unittest
from unittest.mock import MagicMock, patch
import git
from contrib_check.repo import GitRemoteProgress

class TestGitRemoteProgressCoverage(unittest.TestCase):

    def test_progress_update_with_missing_max_count(self):
        """Fixes max_count fallback assignment path: passes None explicitly."""
        progress = GitRemoteProgress()
        # Mock out internal bar dependencies so it doesn't crash on print updates
        progress.bar = MagicMock()

        # Pass None explicitly as max_count
        progress.update(op_code=2, cur_count=50, max_count=None, message="Fetching")

        # Verify the calculation fell back to 100.0 safely (50 / 100.0 = 0.5)
        progress.bar.assert_called_once_with(0.5)

    @patch('contrib_check.repo.alive_bar')
    def test_progress_lifecycle_and_missing_bar_guard(self, mock_alive_bar):
        """Tests the full BEGIN/END cycle and explicitly covers the missing bar guard path."""
        progress = GitRemoteProgress()

        # Scenario A: Update is called WITHOUT a BEGIN flag while progress.bar is uninitialized.
        # This forces 'if self.bar:' to evaluate to False, clearing that branch gap.
        progress.update(op_code=0, cur_count=10, max_count=100, message="Quiet update")
        self.assertIsNone(progress.bar)

        # Scenario B: Fire a proper BEGIN sequence to check bar initialization setup.
        # git.RemoteProgress.BEGIN is a bitmask flag equal to 16
        progress.update(op_code=git.RemoteProgress.BEGIN, cur_count=0, max_count=100, message="Starting")
        self.assertIsNotNone(progress.bar)

        # Scenario C: Fire an END sequence to test structural context exit tracking.
        # git.RemoteProgress.END is a bitmask flag equal to 32
        progress.update(op_code=git.RemoteProgress.END, cur_count=100, max_count=100, message="Done")
        self.assertIsNone(progress.bar)
        self.assertIsNone(progress.alive_bar_instance)

    def test_get_curr_op_unknown_code(self):
        """Verifies the fallback title parsing behavior when an unexpected op code hits."""
        # Mix an out-of-bounds op_code value
        op_title = GitRemoteProgress.get_curr_op(9999)
        self.assertEqual(op_title, "?")
