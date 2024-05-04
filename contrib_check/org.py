#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import socket
import re

from github import Github, GithubException, RateLimitExceededException
from .repo import Repo 

class Org():
    __org_name = ''
    __org_type = 'github'
    ignore_repos = []
    only_repos = []
    skip_archived = True
    lazy_load = False
    repos = []

    def __init__(self,org_name,org_type='github',ignore_repos=[],only_repos=[],skip_archived=True,load_repos=True):
        self.org_type = org_type
        self.org_name = org_name
        self.ignore_repos = ignore_repos
        self.only_repos = only_repos
        self.skip_archived = skip_archived
        if load_repos:
            self.reloadRepos()

    @property
    def org_name(self):
        return self.__org_name

    @org_name.setter
    def org_name(self, org_name):
        self.__org_name = re.sub('^http(s)*://(www\.)*github.com/','',org_name)

    @property
    def org_type(self):
        return self.__org_type

    @org_type.setter
    def org_type(self,org_type):
        if org_type == 'github' and 'GITHUB_TOKEN' not in os.environ:
            raise Exception('Github token is not defined. Set GITHUB_TOKEN environment variable to a valid Github token')

        self.__org_type = org_type

    def reloadRepos(self):
        self.repos = []

        if self.org_type == 'github':
            try:
                gh_repos = self._getGithubReposForOrg()
                for gh_repo in gh_repos:
                    if self.ignore_repos and gh_repo.name in self.ignore_repos:
                        continue
                    if self.only_repos and gh_repo.name not in self.only_repos:
                        continue
                    if self.skip_archived and gh_repo.archived:
                        continue
                    self.repos.append(Repo(gh_repo.html_url))
            except RateLimitExceededException:
                print("Sleeping until we get past the API rate limit....")
                time.sleep(g.rate_limiting_resettime-now())
            except GithubException as e:
                if e.status == 502:
                    print("Server error - retrying...")
                else:
                    print(e.data)
            except socket.timeout:
                print("Server error - retrying...")

        return self.repos
    
    def _getGithubReposForOrg(self):
        g = Github(login_or_token=os.environ['GITHUB_TOKEN'], per_page=1000)
        return g.get_organization(self.org_name).get_repos()
