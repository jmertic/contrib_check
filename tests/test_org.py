#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import socket

import git
from github import GithubException, RateLimitExceededException

from contrib_check.org import Org


def _make_gh_repo(name, html_url=None, archived=False):
    r = Mock()
    r.name = name
    r.html_url = html_url or f"https://github.com/testorg/{name}"
    r.archived = archived
    return r


GH_REPOS = [
    _make_gh_repo("repo1"),
    _make_gh_repo("repo2"),
    _make_gh_repo("repo3", archived=True),
]


class TestOrgInit(unittest.TestCase):

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_init_no_load_repos(self):
        org = Org("testorg", load_repos=False)
        self.assertEqual(org.repos, [])

    def test_init_github_no_token_raises(self):
        env = {k: v for k, v in os.environ.items() if k != 'GITHUB_TOKEN'}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(Exception, 'Github token'):
                Org("testorg")

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_org_name_strips_github_url(self):
        org = Org("https://github.com/myorg", load_repos=False)
        self.assertEqual(org.org_name, "myorg")

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_org_name_strips_www_github_url(self):
        org = Org("https://www.github.com/myorg", load_repos=False)
        self.assertEqual(org.org_name, "myorg")

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_org_name_plain_string_unchanged(self):
        org = Org("myorg", load_repos=False)
        self.assertEqual(org.org_name, "myorg")


class TestOrgReloadRepos(unittest.TestCase):

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    @patch.object(git.Repo, 'clone_from')
    def test_load_repos_excludes_archived_by_default(self, _clone):
        with patch.object(Org, '_get_github_repos_for_org', return_value=GH_REPOS):
            org = Org("testorg")
        self.assertEqual(len(org.repos), 2)
        self.assertEqual(org.repos[0].name, "repo1")
        self.assertEqual(org.repos[1].name, "repo2")

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    @patch.object(git.Repo, 'clone_from')
    def test_load_repos_includes_archived_when_flag_off(self, _clone):
        with patch.object(Org, '_get_github_repos_for_org', return_value=GH_REPOS):
            org = Org("testorg", skip_archived=False)
        self.assertEqual(len(org.repos), 3)

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    @patch.object(git.Repo, 'clone_from')
    def test_ignore_repos(self, _clone):
        with patch.object(Org, '_get_github_repos_for_org', return_value=GH_REPOS):
            org = Org("testorg", ignore_repos=['repo1'])
        self.assertEqual(len(org.repos), 1)
        self.assertEqual(org.repos[0].name, "repo2")

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    @patch.object(git.Repo, 'clone_from')
    def test_only_repos(self, _clone):
        with patch.object(Org, '_get_github_repos_for_org', return_value=GH_REPOS):
            org = Org("testorg", only_repos=['repo1'])
        self.assertEqual(len(org.repos), 1)
        self.assertEqual(org.repos[0].name, "repo1")

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    @patch('contrib_check.org.time.sleep')
    def test_rate_limit_exception_prints_message(self, mock_sleep):
        with patch.object(Org, '_get_github_repos_for_org', side_effect=RateLimitExceededException(403, "rate limit", {})):
            # should not raise; prints a message and returns empty repos
            org = Org("testorg")
        self.assertEqual(org.repos, [])

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_github_exception_502_prints_retry(self):
        exc = GithubException(502, "bad gateway", {})
        with patch.object(Org, '_get_github_repos_for_org', side_effect=exc):
            org = Org("testorg")
        self.assertEqual(org.repos, [])

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_github_exception_other_prints_data(self):
        exc = GithubException(404, "not found", {})
        with patch.object(Org, '_get_github_repos_for_org', side_effect=exc):
            org = Org("testorg")
        self.assertEqual(org.repos, [])

    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test123'})
    def test_socket_timeout_prints_retry(self):
        with patch.object(Org, '_get_github_repos_for_org', side_effect=socket.timeout()):
            org = Org("testorg")
        self.assertEqual(org.repos, [])

    def tearDown(self):
        # clean up any csv files created during tests
        for name in ['repo1', 'repo2', 'repo3']:
            path = f"testorg-{name}.csv"
            if os.path.exists(path):
                os.remove(path)


if __name__ == '__main__':
    unittest.main()
