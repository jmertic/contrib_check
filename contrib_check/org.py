#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import socket
import re
import time
import logging

from github import Github, GithubException, RateLimitExceededException
from .repo import Repo

class Org():

    def __init__(self,
            org_name: str,
            org_type: str = 'github',
            ignore_repos: list[str] | None = None,
            only_repos: list[str] | None = None,
            skip_archived: bool = True,
            load_repos: bool = True
            ):
        self.ignore_repos = ignore_repos or []
        self.only_repos = only_repos or []
        self.repos = []

        self.__org_name = ''
        self.__org_type = 'github'
        self.skip_archived = skip_archived

        # Execute properties assignments to trigger setters validation
        self.org_type = org_type
        self.org_name = org_name

        if load_repos:
            self.reload_repos()

    @property
    def org_name(self):
        return self.__org_name

    @org_name.setter
    def org_name(self, org_name: str):
        self.__org_name = re.sub(r'^http(s)*://(www\.)*github.com/', '', org_name)

    @property
    def org_type(self):
        return self.__org_type

    @org_type.setter
    def org_type(self, org_type):
        if org_type == 'github' and 'GITHUB_TOKEN' not in os.environ:
            raise ValueError('Github token is not defined. Set GITHUB_TOKEN environment variable to a valid Github token')
        self.__org_type = org_type

    def _should_skip_repo(self, gh_repo) -> bool:
        """Helper method to handle repository filtering logic.

        Extracting this removes nested conditionals from the main loop,
        drastically reducing cognitive complexity.
        """
        if self.ignore_repos and gh_repo.name in self.ignore_repos:
            return True
        if self.only_repos and gh_repo.name not in self.only_repos:
            return True
        if self.skip_archived and gh_repo.archived:
            return True
        return False

    def reload_repos(self):
        self.repos = []

        # Guard clause: Exit early if it's not a GitHub org type
        if self.org_type != 'github':
            return self.repos

        try:
            gh_repos = self._get_github_repos_for_org()
            for gh_repo in gh_repos:
                if self._should_skip_repo(gh_repo):
                    continue
                self.repos.append(Repo(gh_repo.html_url))
                logging.getLogger().info(f"Adding repo {gh_repo.html_url}")

        except RateLimitExceededException:
            logging.getLogger().info("Sleeping until we get past the API rate limit....")
            time.sleep(60)
        except GithubException as e:
            if e.status == 502:
                logging.getLogger().error("Server error - retrying...")
            else:
                logging.getLogger().exception(e.data)
        except socket.timeout:
            logging.getLogger().error("Server error - retrying...")

        return self.repos

    def _get_github_repos_for_org(self):
        g = Github(login_or_token=os.environ['GITHUB_TOKEN'], per_page=1000)
        logging.getLogger().info(f"Loading repos for {self.org_name}")
        return g.get_organization(self.org_name).get_repos()
