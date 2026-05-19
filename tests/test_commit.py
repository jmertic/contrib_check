#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import tempfile
import unittest
from unittest.mock import Mock, mock_open, patch

from contrib_check.commit import Commit

def _make_mock_repo(tree_raises_key_error=True):
    """Return a mock repo whose tree[] raises KeyError by default (no dco.yml)."""
    mock_repo = Mock()
    if tree_raises_key_error:
        mock_repo.git_repo_object.head.commit.tree.__getitem__ = Mock(side_effect=KeyError)
    return mock_repo


def _make_commit(parents=None, mock_repo=None):
    if mock_repo is None:
        mock_repo = _make_mock_repo()
    mock_git_commit = Mock()
    mock_git_commit.parents = parents if parents is not None else [1]
    return Commit(mock_git_commit, mock_repo)


class TestCommitDCOSignOff(unittest.TestCase):

    def test_has_no_dco_signoff(self):
        commit = _make_commit()
        commit.git_commit_object.message = "has no signoff"
        self.assertFalse(commit.has_dco_signoff())

    def test_has_dco_signoff(self):
        commit = _make_commit()
        commit.git_commit_object.message = "fix: thing Signed-off-by: John Mertic <jmertic@linuxfoundation.org>"
        self.assertTrue(commit.has_dco_signoff())


class TestCommitDCOPastSignoff(unittest.TestCase):

    SHA = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
    OTHER_SHA = 'c1d322dfba0ed7a770d74074990ac51a9efedcd0'
    SIGNOFF_BLOB = (
        "I, personname hereby sign-off-by all of my past commits to this repo "
        "subject to the Developer Certificate of Origin (DCO), Version 1.1. "
        "In the past I have used emails: [personname@domain.com]\n\n"
        f"{SHA} This is a commit"
    ).encode()

    def test_found_past_signoff(self):
        commit = _make_commit()
        commit.git_commit_object.hexsha = self.SHA
        commit.repo_object.past_signoffs = [self.SIGNOFF_BLOB]
        self.assertTrue(commit.has_dco_past_signoff())

    def test_no_past_signoff(self):
        commit = _make_commit()
        commit.git_commit_object.hexsha = self.OTHER_SHA
        commit.repo_object.past_signoffs = [self.SIGNOFF_BLOB]
        self.assertFalse(commit.has_dco_past_signoff())

    def test_empty_past_signoffs(self):
        commit = _make_commit()
        commit.git_commit_object.hexsha = self.SHA
        commit.repo_object.past_signoffs = []
        self.assertFalse(commit.has_dco_past_signoff())


class TestCommitDCOSignOffRequired(unittest.TestCase):

    def test_not_required_for_merge_commit(self):
        commit = _make_commit(parents=[1, 2, 3])
        self.assertFalse(commit.is_dco_signoff_required())

    def test_required_for_normal_commit(self):
        commit = _make_commit(parents=[1])
        self.assertTrue(commit.is_dco_signoff_required())


class TestCommitCheckDCOSignoff(unittest.TestCase):

    SHA = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
    SIGNOFF_BLOB = (
        "I, personname hereby sign-off-by all of my past commits to this repo "
        "subject to the Developer Certificate of Origin (DCO), Version 1.1. "
        "In the past I have used emails: [personname@domain.com]\n\n"
        f"{SHA} This is a commit"
    ).encode()

    def test_merge_commit_always_passes(self):
        commit = _make_commit(parents=[1, 2])
        commit.git_commit_object.message = "no signoff here"
        self.assertTrue(commit.check_dco_signoff())

    def test_normal_commit_with_signoff_passes(self):
        commit = _make_commit(parents=[1])
        commit.git_commit_object.message = "fix: thing Signed-off-by: Jane <jane@example.com>"
        self.assertTrue(commit.check_dco_signoff())

    def test_normal_commit_without_signoff_fails(self):
        commit = _make_commit(parents=[1])
        commit.git_commit_object.message = "no signoff"
        commit.repo_object.past_signoffs = []
        commit.repo_object.git_repo_object.git.rev_parse.return_value = "abc1234"
        commit.remediations = []
        self.assertFalse(commit.check_dco_signoff())

    def test_normal_commit_with_past_signoff_passes(self):
        commit = _make_commit(parents=[1])
        commit.git_commit_object.message = "no signoff"
        commit.git_commit_object.hexsha = self.SHA
        commit.repo_object.past_signoffs = [self.SIGNOFF_BLOB]
        self.assertTrue(commit.check_dco_signoff())

    def test_normal_commit_with_remediation_passes(self):
        commit = _make_commit(parents=[1])
        commit.git_commit_object.message = "no signoff"
        commit.repo_object.past_signoffs = []
        short = "abc1234"
        commit.repo_object.git_repo_object.git.rev_parse.return_value = short
        commit.remediations = [short]
        self.assertTrue(commit.check_dco_signoff())


class TestCommitHasRemediation(unittest.TestCase):

    def test_has_remediation_match(self):
        commit = _make_commit()
        short = "abc1234"
        commit.repo_object.git_repo_object.git.rev_parse.return_value = short
        commit.remediations = [short]
        self.assertTrue(commit.has_remediation())

    def test_has_remediation_no_match(self):
        commit = _make_commit()
        commit.repo_object.git_repo_object.git.rev_parse.return_value = "abc1234"
        commit.remediations = ["zzzzzzz"]
        self.assertFalse(commit.has_remediation())


class TestCommitLoadRemediationCommitConfig(unittest.TestCase):

    def test_no_dco_yml_returns_false(self):
        """KeyError from tree lookup → returns False, flags stay False."""
        commit = _make_commit()
        self.assertFalse(commit.allow_remediation_commit_individual)
        self.assertFalse(commit.allow_remediation_commit_thirdparty)

    def test_dco_yml_enables_individual(self):
        mock_repo = _make_mock_repo(tree_raises_key_error=False)
        dco_yml = "allowRemediationCommits:\n  individual: true\n  thirdParty: false\n"
        mock_blob = Mock()
        mock_blob.abspath = "/fake/dco.yml"
        mock_repo.git_repo_object.head.commit.tree.__getitem__ = Mock(return_value=mock_blob)
        with patch("builtins.open", mock_open(read_data=dco_yml)):
            commit = _make_commit(mock_repo=mock_repo)
        self.assertTrue(commit.allow_remediation_commit_individual)
        self.assertFalse(commit.allow_remediation_commit_thirdparty)

    def test_dco_yml_enables_thirdparty(self):
        mock_repo = _make_mock_repo(tree_raises_key_error=False)
        dco_yml = "allowRemediationCommits:\n  individual: false\n  thirdParty: true\n"
        mock_blob = Mock()
        mock_blob.abspath = "/fake/dco.yml"
        mock_repo.git_repo_object.head.commit.tree.__getitem__ = Mock(return_value=mock_blob)
        with patch("builtins.open", mock_open(read_data=dco_yml)):
            commit = _make_commit(mock_repo=mock_repo)
        self.assertFalse(commit.allow_remediation_commit_individual)
        self.assertTrue(commit.allow_remediation_commit_thirdparty)

    def test_empty_dco_yml_leaves_flags_false(self):
        mock_repo = _make_mock_repo(tree_raises_key_error=False)
        mock_blob = Mock()
        mock_blob.abspath = "/fake/dco.yml"
        mock_repo.git_repo_object.head.commit.tree.__getitem__ = Mock(return_value=mock_blob)
        with patch("builtins.open", mock_open(read_data="")):
            commit = _make_commit(mock_repo=mock_repo)
        self.assertFalse(commit.allow_remediation_commit_individual)
        self.assertFalse(commit.allow_remediation_commit_thirdparty)


class TestCommitIsRemediationCommit(unittest.TestCase):

    def _commit_with_config(self, individual=False, thirdparty=False):
        mock_repo = _make_mock_repo(tree_raises_key_error=False)
        flags = {}
        if individual:
            flags['individual'] = True
        if thirdparty:
            flags['thirdParty'] = True
        dco_yml = f"allowRemediationCommits:\n  individual: {str(individual).lower()}\n  thirdParty: {str(thirdparty).lower()}\n"
        mock_blob = Mock()
        mock_blob.abspath = "/fake/dco.yml"
        mock_repo.git_repo_object.head.commit.tree.__getitem__ = Mock(return_value=mock_blob)
        with patch("builtins.open", mock_open(read_data=dco_yml)):
            commit = _make_commit(mock_repo=mock_repo)
        return commit

    def test_no_config_not_remediation(self):
        commit = _make_commit()
        commit.git_commit_object.message = "I, Jane <jane@example.com>, hereby add my Signed-off-by to this commit: abc1234"
        commit.git_commit_object.author.name = "Jane"
        commit.git_commit_object.author.email = "jane@example.com"
        self.assertFalse(commit.is_remediation_commit())

    def test_individual_remediation_valid_author(self):
        commit = self._commit_with_config(individual=True)
        commit.git_commit_object.message = "I, Jane Doe <jane@example.com>, hereby add my Signed-off-by to this commit: abc1234"
        commit.git_commit_object.author.name = "Jane Doe"
        commit.git_commit_object.author.email = "jane@example.com"
        self.assertTrue(commit.is_remediation_commit())
        self.assertIn("abc1234", commit.remediations)

    def test_individual_remediation_wrong_author(self):
        commit = self._commit_with_config(individual=True)
        commit.git_commit_object.message = "I, Jane Doe <jane@example.com>, hereby add my Signed-off-by to this commit: abc1234"
        commit.git_commit_object.author.name = "Not Jane"
        commit.git_commit_object.author.email = "other@example.com"
        self.assertFalse(commit.is_remediation_commit())

    def test_thirdparty_remediation_valid_author(self):
        commit = self._commit_with_config(thirdparty=True)
        commit.git_commit_object.message = (
            "On behalf of ACME <acme@acme.com>, I, Bob Smith <bob@acme.com>, "
            "hereby add my Signed-off-by to this commit: def5678"
        )
        commit.git_commit_object.author.name = "Bob Smith"
        commit.git_commit_object.author.email = "bob@acme.com"
        self.assertTrue(commit.is_remediation_commit())
        self.assertIn("def5678", commit.remediations)

    def test_thirdparty_remediation_wrong_author(self):
        commit = self._commit_with_config(thirdparty=True)
        commit.git_commit_object.message = (
            "On behalf of ACME <acme@acme.com>, I, Bob Smith <bob@acme.com>, "
            "hereby add my Signed-off-by to this commit: def5678"
        )
        commit.git_commit_object.author.name = "Not Bob"
        commit.git_commit_object.author.email = "notbob@acme.com"
        self.assertFalse(commit.is_remediation_commit())


if __name__ == '__main__':
    unittest.main()
