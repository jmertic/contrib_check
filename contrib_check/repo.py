#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8
#
# Thin layer that uses GitPython.Repo.Base but adds some metadata and the past signoffs
#

import os
import git
import tempfile
import csv
import re
import shutil

from .commit import Commit

class Repo():
    name = ''
    html_url = ''
    past_signoffs = {}
    git_repo_object = None
    prior_commits_dir = 'dco-signoffs' 

    checks = {
        'dco': True
    }
    
    error_types = {
        'dco': 'The commit did not have a DCO Signoff'    
    }

    __csv_filename = 'output.csv'
    __csv_writer = None

    def __init__(self, repo_path):
        # Skip LFS files - we don't need to download them
        os.environ["GIT_LFS_SKIP_SMUDGE"]="1"
        
        # if GitHub, we can find what we need
        url_search = re.search("https://github.com/(.*)/(.*)",repo_path)
        if url_search:
            self.html_url = repo_path
            self.name = url_search.group(2)
            self.__fo = tempfile.TemporaryDirectory()
            self.git_repo_object = git.Repo.clone_from(self.html_url,self.__fo.name)
            self.csv_filename = url_search.group(1)+'-'+self.name+'.csv'
        # local clone    
        elif os.path.isdir(repo_path):
            self.name = os.path.basename(os.path.normpath(repo_path))
            self.git_repo_object = git.Repo(repo_path)
            self.csv_filename = self.name+'.csv'

    def loadPastSignoffs(self, dco_signoffs_directories = ["dco-signoffs"]):
        try:
            for entry in self.git_repo_object.head.commit.tree:
                if entry.type == 'tree' and entry.name in dco_signoffs_directories:
                    for blob in entry.blobs:
                        with open(blob.abspath(), 'rb') as content_file:
                            content = content_file.read()
                            self.past_signoffs[blob.path] = content
        except ValueError:
            print("...invalid or empty repo - skipping")
            return False

    def scan(self):
        for commit in self.git_repo_object.iter_commits():
            commitObj = Commit(commit,self)
            if 'dco' in self.checks and not commitObj.checkDCOSignoff():
                self.writeError(commitObj,'dco')

    @property
    def csv_filename(self):
        return self.__csv_filename

    @csv_filename.setter
    def csv_filename(self,csvfile):
        # remove file if there already
        if os.path.isfile(csvfile):
            os.remove(csvfile)
        
        self.__csvfileref = open(csvfile, mode='w') 
        self.__csv_writer = csv.writer(self.__csvfileref, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        self.__csv_filename = csvfile
    
    def __del__(self):
        self.__fo.cleanup()
        self.__csvfileref.close() 

    def writeError(self, commit, error_type):
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
            self.writeDCOPriorCommitsFile(commit)

    def writeDCOPriorCommitsFile(self, commit):
        if not os.path.exists(self.prior_commits_dir):
            os.mkdir(self.prior_commits_dir)
        if not os.path.exists(self.prior_commits_dir+'/'+self.name):
            os.mkdir(self.prior_commits_dir+'/'+self.name)

        commitfilename = self.prior_commits_dir+'/'+self.name+'/'+commit.git_commit_object.author.name+'-'+self.name+'.txt'

        if not os.path.isfile(commitfilename):
            fh = open(commitfilename,  mode='w+')
            fh.write("I, "+commit.git_commit_object.author.name+" hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: "+commit.git_commit_object.author.email+"\n\n")
        else:
            fh = open(commitfilename,  mode='a')

        fh.write(commit.git_commit_object.hexsha+" "+commit.git_commit_object.message+"\n")
        fh.close()
