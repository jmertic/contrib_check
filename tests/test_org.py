#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8
#

import os
import unittest
from unittest.mock import MagicMock, patch
from github import RateLimitExceededException, GithubException
from contrib_check.org import Org

class TestOrgCoverage(unittest.TestCase):

    def setUp(self):
        # Seed the token environment variable required by the setter validation
        os.environ['GITHUB_TOKEN'] = 'fake_secure_token'

    def tearDown(self):
        # Clear it out so it doesn't pollute real execution states
        if 'GITHUB_TOKEN' in os.environ:
            del os.environ['GITHUB_TOKEN']

    def test_init_missing_token_exception(self):
        """Verifies an explicit error is raised if GITHUB_TOKEN is absent."""
        del os.environ['GITHUB_TOKEN']
        with self.assertRaises(Exception) as context:
            Org("my-org", org_type="github")
        self.assertIn("Github token is not defined", str(context.exception))

    @patch('contrib_check.org.Org._get_github_repos_for_org')
    def test_reload_repos_skip_non_github_type(self, mock_get_repos):
        """Fixes 56 ↛ 78 in original: Skips the github logic block entirely when type differs."""
        org = Org("my-org", load_repos=False)
        org._Org__org_type = 'custom_git'

        result = org.reload_repos()
        self.assertEqual(result, [])
        mock_get_repos.assert_not_called()

    @patch('contrib_check.org.Repo')
    @patch('contrib_check.org.Org._get_github_repos_for_org')
    def test_reload_repos_filters_and_loops(self, mock_get_repos, mock_repo_class):
        """Exercises every loop condition inside reload_repos (ignore, only, and archived filters)."""
        mock_repo_1 = MagicMock()
        mock_repo_1.name = "ignored-project"
        mock_repo_1.archived = False

        mock_repo_2 = MagicMock()
        mock_repo_2.name = "skipped-project"
        mock_repo_2.archived = False

        mock_repo_3 = MagicMock()
        mock_repo_3.name = "archived-project"
        mock_repo_3.archived = True

        mock_repo_4 = MagicMock()
        mock_repo_4.name = "valid-project"
        mock_repo_4.archived = False
        mock_repo_4.html_url = "https://github.com/my-org/valid-project"

        mock_get_repos.return_value = [mock_repo_1, mock_repo_2, mock_repo_3, mock_repo_4]

        org = Org(
            org_name="my-org",
            ignore_repos=["ignored-project"],
            only_repos=["valid-project"],
            skip_archived=True
        )

        self.assertEqual(len(org.repos), 1)
        mock_repo_class.assert_called_once_with("https://github.com/my-org/valid-project")

    @patch('contrib_check.org.Repo')
    @patch('contrib_check.org.Org._get_github_repos_for_org')
    def test_reload_repos_include_archived_when_disabled(self, mock_get_repos, mock_repo_class):
        """Fixes 72 ↛ 73: Verifies archived repos are NOT skipped if skip_archived=False."""
        mock_archived_repo = MagicMock()
        mock_archived_repo.name = "old-archived-project"
        mock_archived_repo.archived = True
        mock_archived_repo.html_url = "https://github.com/my-org/old-archived-project"

        mock_get_repos.return_value = [mock_archived_repo]

        # Explicitly pass skip_archived=False to step past line 72
        org = Org(org_name="my-org", skip_archived=False)

        # The archived repo should bypass the filter and be added cleanly
        self.assertEqual(len(org.repos), 1)
        mock_repo_class.assert_called_once_with("https://github.com/my-org/old-archived-project")

    @patch('contrib_check.org.Org._get_github_repos_for_org')
    def test_reload_repos_rate_limiting_exception(self, mock_get_repos):
        """Triggers the API rate limit handler block."""
        mock_get_repos.side_effect = RateLimitExceededException(status=403, data="Rate limit hit", headers={})

        with patch('time.sleep') as mock_sleep:
            org = Org("my-org")
            mock_sleep.assert_called_once_with(60)
            self.assertEqual(org.repos, [])

    @patch('contrib_check.org.Org._get_github_repos_for_org')
    def test_reload_repos_server_error_502_exception(self, mock_get_repos):
        """Triggers the 502 branch of the GithubException block."""
        mock_get_repos.side_effect = GithubException(status=502, data={"message": "Bad Gateway"}, headers={})
        org = Org("my-org")
        self.assertEqual(org.repos, [])

    @patch('contrib_check.org.Org._get_github_repos_for_org')
    def test_reload_repos_other_github_exception_else_branch(self, mock_get_repos):
        """Fixes 79 ↛ 82: Triggers the non-502 'else' block inside GithubException."""
        # Use a 404 code to fail the 'if e.status == 502' condition
        mock_get_repos.side_effect = GithubException(status=404, data={"message": "Not Found"}, headers={})

        org = Org("my-org")
        self.assertEqual(org.repos, [])

