#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8
#
# Provides a decorator-esque pattern on the GitPython.Commit object to add the commit inspection capabilities

import re

# third party modules
import yaml
import git

class Commit():
    # GitPython.Commit object
    git_commit_object = None

    repo_object = None
    is_merge_commit = False

    create_prior_commits_dir = 'dco-signoffs'
    
    remediation_regex_individual = "^I, (.*) <(.*)>, hereby add my Signed-off-by to this commit: (.*)\s*$"
    remediation_regex_thirdparty = "^On behalf of (.*) <(.*)>, I, (.*) <(.*)>, hereby add my Signed-off-by to this commit: (.*)\s*$"

    allow_remediation_commit_individual = False
    allow_remediation_commit_thirdparty = False

    remediations = []

    def __init__(self, git_commit_object, repo_object):
        self.git_commit_object = git_commit_object
        self.repo_object = repo_object
        self.is_merge_commit = len(git_commit_object.parents) > 1
        self.loadRemediationCommitConfig()

    def checkDCOSignoff(self):
        if self.isDCOSignOffRequired():
            return self.hasDCOSignOff() or self.hasDCOPastSignoff() or self.hasRemediation()
    
        return True

    def isDCOSignOffRequired(self):
        return not self.is_merge_commit
    
    def hasDCOSignOff(self):
        return (re.search("Signed-off-by: (.+)",self.git_commit_object.message) != None)

    def hasDCOPastSignoff(self):
        for signoff in self.repo_object.past_signoffs:
            if (re.search(self.git_commit_object.hexsha.encode(),signoff) != None):
                return True

        return False

    def hasRemediation(self):
        return self.repo_object.git_repo_object.git.rev_parse(self.git_commit_object.hexsha, short="7") in self.remediations
    
    def loadRemediationCommitConfig(self):
        try:
            with open(self.repo_object.git_repo_object.head.commit.tree[".github/dco.yml"].abspath, 'r') as file: 
                config = yaml.safe_load(file)
            self.allow_remediation_commit_individual = config['allowRemediationCommits']['individual'] if config and 'allowRemediationCommits' in config and 'individual' in config['allowRemediationCommits'] else False
            self.allow_remediation_commit_thirdparty = config['allowRemediationCommits']['thirdParty'] if config and 'allowRemediationCommits' in config and 'thirdParty' in config['allowRemediationCommits'] else False
        except KeyError as e:
            return False
        else:
            return True

    def isRemediationCommit(self):
        isremediationcommit = False

        if self.allow_remediation_commit_individual:
            for match in re.findall(self.remediation_regex_individual,self.git_commit_object.message,flags=re.I|re.M): 
                # ensure it's a valid remediation commit by matching the author with the attestaion
                if ( match[0] == self.git_commit_object.author.name ) and ( match[1] == self.git_commit_object.author.email ):
                    self.remediations.append(match[2])
                    isremediationcommit = True
        if self.allow_remediation_commit_thirdparty:
            for match in re.findall(self.remediation_regex_thirdparty,self.git_commit_object.message,flags=re.I|re.M):
                # ensure it's a valid remediation commit by matching the author with the attestaion
                if ( match[2] == self.git_commit_object.author.name ) and ( match[3] == self.git_commit_object.author.email ):
                    self.remediations.append(match[4])
                    isremediationcommit = True
        
        return isremediationcommit
