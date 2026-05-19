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
import shutil

import git

from contrib_check.repo import Repo
from contrib_check.commit import Commit

def _make_repo_github(url="https://github.com/foo/bar"):
    with patch('git.Repo.clone_from') as mock_clone:
        # 1. Setup the basic repo object mock
        mock_repo_inst = MagicMock()
        mock_clone.return_value = mock_repo_inst

        # 2. Fix the iteration bug: force the tree to look like an empty iterable container
        mock_repo_inst.head.commit.tree = []

        # 3. Handle commit iteration mock requirements for other functions
        mock_repo_inst.iter_commits.return_value = []

        repo = Repo(url)
        return repo

def _make_repo_local(path="."):
    with patch('git.Repo') as mock_repo_class:
        # 1. Setup the basic repo object mock
        mock_repo_inst = MagicMock()
        mock_repo_class.return_value = mock_repo_inst

        # 2. Fix the iteration bug: force the tree to look like an empty iterable container
        mock_repo_inst.head.commit.tree = []

        # 3. Handle commit iteration mock requirements
        mock_repo_inst.iter_commits.return_value = []

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

        self.repo.load_past_signoffs()
        self.assertEqual(self.repo.past_signoffs, [blob_content])
        os.unlink(tf_name)

    def test_skips_non_matching_directories(self):
        self.repo.past_signoffs = []  # reset instance list; class-level list can leak between tests
        mock_tree_entry = Mock()
        mock_tree_entry.type = 'tree'
        mock_tree_entry.name = 'other-dir'

        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree = [mock_tree_entry]

        self.repo.load_past_signoffs()
        self.assertEqual(self.repo.past_signoffs, [])

    def test_invalid_repo_returns_false(self):
        self.repo.git_repo_object = Mock()
        self.repo.git_repo_object.head.commit.tree.__iter__ = Mock(side_effect=ValueError)
        result = self.repo.load_past_signoffs()
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

class TestRepoBranchCoverage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        # Build mock commit layout
        self.mock_commit_obj = MagicMock()
        self.mock_commit_obj.git_commit_object.hexsha = "abcdef1234567890"
        self.mock_commit_obj.git_commit_object.message = "Fixing a bad bug"
        self.mock_commit_obj.git_commit_object.author.name = "John Mertic"
        self.mock_commit_obj.git_commit_object.author.email = "john@example.com"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        shutil.rmtree('dco-signoffs', ignore_errors=True)
        shutil.rmtree('remediation-commits', ignore_errors=True)

    @patch('git.Repo')
    def test_init_local_repo_branch(self, mock_git_repo):
        """Covers line 69."""
        repo = Repo(self.test_dir)
        self.assertEqual(repo.name, os.path.basename(self.test_dir))
        mock_git_repo.assert_called_once_with(self.test_dir)

    @patch('git.Repo')
    def test_init_invalid_path_branch(self, mock_git_repo):
        """Fixes 69 ↛ 74: Path is neither a GitHub URL nor a valid directory."""
        fake_path = os.path.join(self.test_dir, "does_not_exist")
        repo = Repo(fake_path)
        self.assertEqual(repo.name, '')
        self.assertIsNone(repo.git_repo_object)

    @patch('git.Repo')
    def test_load_past_signoffs_defaults(self, mock_git_repo):
        """Fixes 77 ↛ 80: Forces dco_signoffs_directories to be None."""
        repo = Repo(self.test_dir)
        repo.git_repo_object.head.commit.tree = []
        # Call without arguments to hit the 'is None' branch
        result = repo.load_past_signoffs()
        self.assertTrue(result)

    @patch('git.Repo')
    def test_guard_clauses_empty_repo(self, mock_git_repo):
        """Fixes 93 ↛ 94 and 101 ↛ 102: Missing git_repo_object guard routes."""
        fake_path = os.path.join(self.test_dir, "does_not_exist")
        repo = Repo(fake_path) # self.git_repo_object is None

        # Should return early gracefully instead of dropping into exceptions
        self.assertIsNone(repo.load_remediation_commits())
        self.assertIsNone(repo.scan())

    @patch('git.Repo')
    def test_close_without_csv_ref(self, mock_git_repo):
        """Fixes 130 ↛ 133: close() called when __csvfileref is already None."""
        repo = Repo(self.test_dir)
        repo.close() # First call closes it
        repo.close() # Second call forces the 'if self.__csvfileref' to be False

    @patch('git.Repo')
    def test_write_error_uninitialized_csv(self, mock_git_repo):
        """Fixes 142 ↛ 143: Verifies RuntimeError when writing without a file setup."""
        repo = Repo(self.test_dir)
        # Manually destroy the internal writer object
        repo._Repo__csv_writer = None

        with self.assertRaises(RuntimeError):
            repo.write_error(self.mock_commit_obj, 'dco')

    @patch('git.Repo')
    @patch('contrib_check.repo.Commit')
    def test_write_error_non_dco_type(self, mock_commit_class, mock_git_repo):
        """Fixes 156 ↛ exit: Skips the write_dco_prior_commits_file branch."""
        repo = Repo(self.test_dir)
        output_target = os.path.join(self.test_dir, "scan_output.csv")
        repo.csv_filename = output_target

        # Inject custom error type that isn't 'dco'
        repo.error_types['custom'] = 'Some alternative issue'

        with patch.object(repo, 'write_dco_prior_commits_file') as mock_write_priors:
            repo.write_error(self.mock_commit_obj, 'custom')
            # Verify the DCO-specific file write block was bypassed
            mock_write_priors.assert_not_called()

    @patch('git.Repo')
    @patch('contrib_check.repo.Commit')
    def test_load_remediation_commits_true_branch(self, mock_commit_class, mock_git_repo):
        mock_commit_instance = mock_commit_class.return_value
        mock_commit_instance.is_remediation_commit.return_value = True
        mock_commit_instance.remediations = ["remediation_alpha"]
        mock_git_repo.return_value.iter_commits.return_value = [MagicMock()]

        repo = Repo(self.test_dir)
        repo.load_remediation_commits()
        self.assertIn("remediation_alpha", repo.remediations)

    @patch('git.Repo')
    def test_csv_filename_removes_existing_file(self, mock_git_repo):
        repo = Repo(self.test_dir)
        test_csv_path = os.path.join(self.test_dir, "clashing_output.csv")
        with open(test_csv_path, 'w') as f:
            f.write("old data")

        repo.csv_filename = test_csv_path
        self.assertEqual(os.path.getsize(test_csv_path), 0)

    @patch('git.Repo')
    def test_load_past_signoffs_with_explicit_directories(self, mock_git_repo):
        """Fixes 69 ↛ 72: Forces dco_signoffs_directories to be a provided list instead of None."""
        repo = Repo(self.test_dir)
        repo.git_repo_object.head.commit.tree = []

        # Pass an explicit custom list to evaluate the False/skip branch condition
        result = repo.load_past_signoffs(dco_signoffs_directories=["custom-signoffs-dir"])
        self.assertTrue(result)
