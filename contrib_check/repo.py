#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8
#
# Thin layer that uses GitPython.Repo.Base but adds some metadata and the past signoffs
#

from __future__ import annotations

import os
import tempfile
import csv
import re
import shutil

from alive_progress import alive_bar
import git
from git import RemoteProgress

from .commit import Commit

class Repo():
    # Class-level immutable defaults (Safe)
    prior_commits_dir = 'dco-signoffs'
    remediation_commits_dir = 'remediation-commits'

    checks = { 'dco': True }
    error_types = { 'dco': 'The commit did not have a DCO Signoff' }

    def __init__(self, repo_path):
        # Properly scope mutable collections to the INSTANCE
        self.name = ''
        self.html_url = ''
        self.past_signoffs = []
        self.remediations = []
        self.git_repo_object = None

        self.__csv_filename = 'output.csv'
        self.__csv_writer = None
        self.__fo = None
        self.__csvfileref = None

        # Skip LFS files - we don't need to download them
        os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"

        # if GitHub, we can find what we need
        url_search = re.search(r"https://github\.com/(.*)/(.*)", repo_path)
        if url_search:
            self.html_url = repo_path
            self.name = url_search.group(2)
            self.__fo = tempfile.TemporaryDirectory()
            print(f"Cloning repo {self.html_url}")
            self.git_repo_object = git.Repo.clone_from(
                self.html_url, self.__fo.name, progress=GitRemoteProgress()
            )
            self.csv_filename = f"{url_search.group(1)}-{self.name}.csv"
        # local clone
        elif os.path.isdir(repo_path):
            self.name = os.path.basename(os.path.realpath(repo_path))
            self.git_repo_object = git.Repo(repo_path)
            self.csv_filename = f"{self.name}.csv"

        self.load_remediation_commits()

    def load_past_signoffs(self, dco_signoffs_directories=None):
        if dco_signoffs_directories is None:
            dco_signoffs_directories = ["dco-signoffs"]

        try:
            for entry in self.git_repo_object.head.commit.tree:
                if entry.type == 'tree' and entry.name in dco_signoffs_directories:
                    for blob in entry.blobs:
                        with open(blob.abspath, 'rb') as content_file:
                            content = content_file.read()
                            self.past_signoffs.append(content)
        except (ValueError, AttributeError):
            print("...invalid or empty repo - skipping")
            return False
        return True

    def load_remediation_commits(self):
        if not self.git_repo_object:
            return
        for commit in self.git_repo_object.iter_commits():
            commit_obj = Commit(commit, self)
            if commit_obj.is_remediation_commit():
                self.remediations.extend(commit_obj.remediations)

    def scan(self):
        if not self.git_repo_object:
            return
        for commit in self.git_repo_object.iter_commits():
            commit_obj = Commit(commit, self)
            if 'dco' in self.checks and not commit_obj.check_dco_signoff():
                self.write_error(commit_obj, 'dco')

    @property
    def csv_filename(self):
        return self.__csv_filename

    @csv_filename.setter
    def csv_filename(self, csvfile):
        # Safely clear out any old references first
        if self.__csvfileref:
            self.__csvfileref.close()

        if os.path.isfile(csvfile):
            os.remove(csvfile)

        # We keep this reference open because write_error needs continuous access
        self.__csvfileref = open(csvfile, mode='w', encoding='utf-8', newline='')
        self.__csv_writer = csv.writer(
            self.__csvfileref, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL
        )
        self.__csv_filename = csvfile

    def close(self):
        """Explicit cleanup method to ensure resources drain properly."""
        if self.__csvfileref:
            self.__csvfileref.close()
            self.__csvfileref = None
        if self.__fo:
            self.__fo.cleanup()
            self.__fo = None

    def __del__(self):
        # Fallback safety net
        self.close()

    def write_error(self, commit, error_type):
        if not self.__csv_writer:
            raise RuntimeError("CSV file has not been initialized via csv_filename setter.")

        self.__csv_writer.writerow([
            self.name,
            commit.git_commit_object.hexsha,
            commit.git_commit_object.message,
            commit.git_commit_object.author.name,
            commit.git_commit_object.author.email,
            commit.git_commit_object.authored_datetime,
            error_type,
            self.error_types[error_type]
        ])

        if error_type == 'dco':
            self.write_dco_prior_commits_file(commit)

    def write_individual_remediation_commit(self, commit):
        os.makedirs(self.remediation_commits_dir, exist_ok=True)

        remediationfilename = os.path.join(
            self.remediation_commits_dir, f"{self.name}-{commit.git_commit_object.author.name}.txt"
        )
        short_hash = self.git_repo_object.git.rev_parse(commit.git_commit_object.hexsha, short="7")

        mode = 'a' if os.path.isfile(remediationfilename) else 'w+'

        with open(remediationfilename, mode=mode, encoding='utf-8') as fh:
            if mode == 'w+':
                fh.write(f"DCO Remediation Commit for {commit.git_commit_object.author.name} <{commit.git_commit_object.author.email}>\n\n")
            fh.write(f"I, {commit.git_commit_object.author.name} <{commit.git_commit_object.author.email}>, hereby add my Signed-off-by to this commit: {short_hash}\n")

    def write_dco_prior_commits_file(self, commit):
        target_dir = os.path.join(self.prior_commits_dir, self.name)
        os.makedirs(target_dir, exist_ok=True)

        commitfilename = os.path.join(target_dir, f"{commit.git_commit_object.author.name}-{self.name}.txt")
        mode = 'a' if os.path.isfile(commitfilename) else 'w+'

        with open(commitfilename, mode=mode, encoding='utf-8') as fh:
            if mode == 'w+':
                fh.write(f"I, {commit.git_commit_object.author.name} hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: {commit.git_commit_object.author.email}\n\n")
            fh.write(f"{commit.git_commit_object.hexsha} {commit.git_commit_object.message}\n")


class GitRemoteProgress(git.RemoteProgress):
    OP_CODES = [
        "BEGIN", "CHECKING_OUT", "COMPRESSING", "COUNTING", "END",
        "FINDING_SOURCES", "RECEIVING", "RESOLVING", "WRITING"
    ]
    OP_CODE_MAP = {
        getattr(git.RemoteProgress, _op_code): _op_code for _op_code in OP_CODES
    }

    def __init__(self) -> None:
        super().__init__()
        self.alive_bar_instance = None
        self.bar = None

    @classmethod
    def get_curr_op(cls, op_code: int) -> str:
        op_code_masked = op_code & cls.OP_MASK
        return cls.OP_CODE_MAP.get(op_code_masked, "?").title()

    def update(
        self,
        op_code: int,
        cur_count: str | float,
        max_count: str | float | None = None,
        message: str | None = "",
    ) -> None:
        cur_count = float(cur_count)
        max_count = float(max_count) if max_count is not None else 100.0

        if op_code & self.BEGIN:
            self.curr_op = self.get_curr_op(op_code)
            self._dispatch_bar(title=self.curr_op)

        if self.bar:
            self.bar(cur_count / max_count)
            self.bar.text(str(message or ""))

        if op_code & git.RemoteProgress.END:
            self._destroy_bar()

    def _dispatch_bar(self, title: str | None = "") -> None:
        self.alive_bar_instance = alive_bar(manual=True, title=title)
        self.bar = self.alive_bar_instance.__enter__()

    def _destroy_bar(self) -> None:
        if self.alive_bar_instance:
            self.alive_bar_instance.__exit__(None, None, None)
            self.alive_bar_instance = None
            self.bar = None
