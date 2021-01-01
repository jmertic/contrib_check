#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8
#
# Provides a decorator-esque pattern on the GitPython.Commit object to add the commit inspection capabilities

import re

import git

class Commit():
    # GitPython.Commit object
    git_commit_object = None

    repo_object = None
    is_merge_commit = False

    create_prior_commits_dir = 'dco-signoffs'
    
    def __init__(self, git_commit_object, repo_object):
        self.git_commit_object = git_commit_object
        self.repo_object = repo_object
        self.is_merge_commit = len(git_commit_object.parents) > 1
    
    def checkDCOSignoff(self):
        if self.isDCOSignOffRequired():
            return self.hasDCOSignOff() or self.hasDCOPastSignoff()
    
        return True

    def isDCOSignOffRequired(self):
        return not self.is_merge_commit
    
    def hasDCOSignOff(self):
        return re.search("Signed-off-by: (.+)",self.git_commit_object.message)

    def hasDCOPastSignoff(self):
        for signoff in self.repo_object.past_signoffs:
            if not signoff[1].find(self.git_commit_object.hexsha.encode()) == -1:
                return True

        return False;

