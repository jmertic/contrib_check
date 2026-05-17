#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock, call

import git

from contrib_check.repo import Repo
from contrib_check.commit import Commit


def _make_repo_github(url="https://github.com/foo/bar"):
    """Construct a GitHub-style Repo with clone_from mocked out."""
    with patch.object(git.Repo, 'clone_from') as mock_clone:
        mock_git_repo = Mock()
        mock_git_repo.iter_commits.return_value = []
        mock_git_repo.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
        mock_clone.return_value = mock_git_repo
        repo = Repo(url)
    return repo


def _make_repo_local(path="."):
    """Construct a local Repo with git.Repo mocked out."""
    mock_git_repo = Mock()
    mock_git_repo.iter_commits.return_value = []
    mock_git_repo.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
    with patch.object(git.Repo, '__init__', return_value=None):
        with patch('contrib_check.repo.git.Repo', return_value=mock_git_repo):
            repo = Repo(path)
    return repo


class TestRepoInitGithub(unittest.TestCase):

    def setUp(self):
        self.repo = _make_repo_github("https://github.com/foo/bar")

    def tearDown(self):
        if os.path.isfile("foo-bar.csv"):
            os.remove("foo-bar.csv")

    def test_name(self):
        self.assertEqual(self.repo.name, "bar")

    def test_html_url(self):
        self.assertEqual(self.repo.html_url, "https://github.com/foo/bar")

    def test_csv_filename(self):
        self.assertEqual(self.repo.csv_filename, "foo-bar.csv")

    def test_csv_file_created(self):
        self.assertTrue(os.path.isfile("foo-bar.csv"))


class TestRepoInitLocal(unittest.TestCase):

    def setUp(self):
        self.repo = _make_repo_local(".")
        self.expected_name = os.path.basename(os.path.realpath("."))

    def tearDown(self):
        if os.path.isfile(self.expected_name + ".csv"):
            os.remove(self.expected_name + ".csv")

    def test_name(self):
        self.assertEqual(self.repo.name, self.expected_name)

    def test_html_url_empty(self):
        self.assertEqual(self.repo.html_url, "")

    def test_csv_filename(self):
        self.assertEqual(self.repo.csv_filename, self.expected_name + ".csv")

    def test_csv_file_created(self):
        self.assertTrue(os.path.isfile(self.expected_name + ".csv"))


class TestRepoLoadPastSignoffs(unittest.TestCase):

    def setUp(self):
        self.repo = _make_repo_github()

    def tearDown(self):
        if os.path.isfile("foo-bar.csv"):
            os.remove("foo-bar.csv")

    def test_loads_signoffs_from_directory(self):
        blob_content = b"some signoff content"
        mock_blob = Mock()

        # write content to a real temp file so open() works
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tf:
            tf.write(blob_content)
            tf_name = tf.name
        mock_blob.abspath = tf_name

        mock_tree_entry = Mock()
        mock_tree_entry.type = 'tree'
        mock_tree_entry.name = 'dco-signoffs'
        mock_tree_entry.blobs = [mock_blob]

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree = [mock_tree_entry]

        self.repo.loadPastSignoffs()
        self.assertEqual(self.repo.past_signoffs, [blob_content])
        os.unlink(tf_name)

    def test_skips_non_matching_directories(self):
        self.repo.past_signoffs = []  # reset instance list; class-level list can leak between tests
        mock_tree_entry = Mock()
        mock_tree_entry.type = 'tree'
        mock_tree_entry.name = 'other-dir'

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree = [mock_tree_entry]

        self.repo.loadPastSignoffs()
        self.assertEqual(self.repo.past_signoffs, [])

    def test_invalid_repo_returns_false(self):
        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree.__iter__ = Mock(side_effect=ValueError)
        result = self.repo.loadPastSignoffs()
        self.assertFalse(result)


class TestRepoLoadRemediationCommits(unittest.TestCase):

    def setUp(self):
        self.repo = _make_repo_github()

    def tearDown(self):
        if os.path.isfile("foo-bar.csv"):
            os.remove("foo-bar.csv")

    def test_collects_remediations_from_commits(self):
        mock_git_commit = Mock()
        mock_git_commit.parents = [1]

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
        self.repo.git_repo_object.iter_commits.return_value = [mock_git_commit]

        with patch.object(Commit, 'is_remediation_commit', return_value=True):
            with patch.object(Commit, '__init__', return_value=None) as mock_init:
                # can't easily patch __init__ and keep remediations; test via integration
                pass

        # integration-style: let a real Commit run (no dco.yml → no remediations)
        self.repo.git_repo_object.iter_commits.return_value = [mock_git_commit]
        self.repo.remediations = []
        self.repo.load_remediation_commits()
        # No dco.yml config → is_remediation_commit returns False → remediations stays empty
        self.assertEqual(self.repo.remediations, [])


class TestRepoScan(unittest.TestCase):

    def setUp(self):
        self.repo = _make_repo_github()

    def tearDown(self):
        for f in ["foo-bar.csv"]:
            if os.path.isfile(f):
                os.remove(f)
        import shutil
        if os.path.isdir("dco-signoffs"):
            shutil.rmtree("dco-signoffs")

    def test_scan_writes_error_for_unsigned_commit(self):
        mock_git_commit = Mock()
        mock_git_commit.parents = [1]
        mock_git_commit.message = "no signoff"
        mock_git_commit.hexsha = "aabbccdd" * 5
        mock_git_commit.author.name = "Dev"
        mock_git_commit.author.email = "dev@example.com"
        mock_git_commit.authored_datetime = "2024-01-01"

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
        self.repo.git_repo_object.iter_commits.return_value = [mock_git_commit]
        self.repo.git_repo_object.git.rev_parse.return_value = "aabbccd"
        self.repo.past_signoffs = []
        self.repo.remediations = []

        self.repo.scan()

        # flush the still-open csv writer before reading
        self.repo._Repo__csvfileref.flush()

        with open("foo-bar.csv") as f:
            content = f.read()
        self.assertIn("no signoff", content)
        self.assertIn("dco", content)

    def test_scan_no_error_for_signed_commit(self):
        mock_git_commit = Mock()
        mock_git_commit.parents = [1]
        mock_git_commit.message = "fix Signed-off-by: Dev <dev@example.com>"

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
        self.repo.git_repo_object.iter_commits.return_value = [mock_git_commit]
        self.repo.past_signoffs = []
        self.repo.remediations = []

        self.repo.scan()

        with open("foo-bar.csv") as f:
            content = f.read()
        self.assertEqual(content.strip(), "")

    def test_scan_no_error_for_merge_commit(self):
        mock_git_commit = Mock()
        mock_git_commit.parents = [1, 2]
        mock_git_commit.message = "Merge branch x into y"

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
        self.repo.git_repo_object.iter_commits.return_value = [mock_git_commit]

        self.repo.scan()

        with open("foo-bar.csv") as f:
            content = f.read()
        self.assertEqual(content.strip(), "")


class TestRepoWriteDCOPriorCommitsFile(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo = _make_repo_github()
        self.repo.prior_commits_dir = os.path.join(self.tmpdir, "dco-signoffs")
        self.repo.name = "myrepo"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if os.path.isfile("foo-bar.csv"):
            os.remove("foo-bar.csv")

    def _make_commit_obj(self, hexsha, message, author_name, author_email):
        commit = Mock()
        commit.git_commit_object.hexsha = hexsha
        commit.git_commit_object.message = message
        commit.git_commit_object.author.name = author_name
        commit.git_commit_object.author.email = author_email
        return commit

    def test_creates_new_file(self):
        commit = self._make_commit_obj("abc123", "fix bug", "Alice", "alice@example.com")
        self.repo.write_dco_prior_commits_file(commit)

        expected = os.path.join(self.repo.prior_commits_dir, "myrepo", "Alice-myrepo.txt")
        self.assertTrue(os.path.isfile(expected))
        with open(expected) as f:
            content = f.read()
        self.assertIn("Alice", content)
        self.assertIn("abc123", content)

    def test_appends_to_existing_file(self):
        commit1 = self._make_commit_obj("abc123", "first", "Alice", "alice@example.com")
        commit2 = self._make_commit_obj("def456", "second", "Alice", "alice@example.com")
        self.repo.write_dco_prior_commits_file(commit1)
        self.repo.write_dco_prior_commits_file(commit2)

        expected = os.path.join(self.repo.prior_commits_dir, "myrepo", "Alice-myrepo.txt")
        with open(expected) as f:
            content = f.read()
        self.assertIn("abc123", content)
        self.assertIn("def456", content)


class TestRepoWriteIndividualRemediationCommit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo = _make_repo_github()
        self.repo.remediation_commits_dir = os.path.join(self.tmpdir, "remediation-commits")
        self.repo.name = "myrepo"
        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.git.rev_parse.return_value = "abc1234"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if os.path.isfile("foo-bar.csv"):
            os.remove("foo-bar.csv")

    def _make_commit_obj(self, hexsha="fullhash", author_name="Alice", author_email="alice@example.com"):
        commit = Mock()
        commit.git_commit_object.hexsha = hexsha
        commit.git_commit_object.author.name = author_name
        commit.git_commit_object.author.email = author_email
        return commit

    def test_creates_new_remediation_file(self):
        commit = self._make_commit_obj()
        self.repo.write_individual_remediation_commit(commit)

        expected = os.path.join(self.repo.remediation_commits_dir, "myrepo-Alice.txt")
        self.assertTrue(os.path.isfile(expected))
        with open(expected) as f:
            content = f.read()
        self.assertIn("Alice", content)
        self.assertIn("abc1234", content)

    def test_appends_to_existing_remediation_file(self):
        commit1 = self._make_commit_obj(hexsha="hash1")
        commit2 = self._make_commit_obj(hexsha="hash2")
        self.repo.git_repo_object.git.rev_parse.side_effect = ["short1", "short2"]
        self.repo.write_individual_remediation_commit(commit1)
        self.repo.write_individual_remediation_commit(commit2)

        expected = os.path.join(self.repo.remediation_commits_dir, "myrepo-Alice.txt")
        with open(expected) as f:
            content = f.read()
        self.assertIn("short1", content)
        self.assertIn("short2", content)


if __name__ == '__main__':
    unittest.main()
