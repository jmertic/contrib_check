#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import git

import unittest
from unittest.mock import Mock

from contrib_check.org import Org
from contrib_check.repo import Repo
from contrib_check.commit import Commit


class TestCommit(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self._mock_repo = Mock()

        self._mock_commit_merge = Mock()
        self._mock_commit_merge.parents = [1,2,3]

        self._mock_commit = Mock()
        self._mock_commit.parents = [1]

    # test for not having a signoff
    def testHasNoDCOSignOff(self):
        commit = Commit(self._mock_commit,self._mock_repo)
        commit.git_commit_object.message = "has no signoff"
        self.assertFalse(commit.hasDCOSignOff(), "Commit message didn't have a signoff")

    # test for having a signoff
    def testHasDCOSignOff(self):
        commit = Commit(self._mock_commit,self._mock_repo)
        commit.git_commit_object.message = "has a signoff  Signed-off-by: John Mertic <jmertic@linuxfoundation.org>"
        self.assertTrue(commit.hasDCOSignOff(), "Commit message had a signoff")

    def testFoundPastDCOSignoff(self):
        commit = Commit(self._mock_commit,self._mock_repo)
        commit.git_commit_object.hexsha = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
        commit.repo_object.past_signoffs = [
            ['dco-signoffs',"I, personname hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: [personname@domain.com]\n\n11ac960e1070eacc2fe92ac9a3d1753400e1fd4b This is a commit".encode() ]
        ]

        self.assertTrue(commit.hasDCOPastSignoff(), "Commit message had a past signoff")

    def testFoundNoPastDCOSignoff(self):
        commit = Commit(self._mock_commit,self._mock_repo)
        commit.git_commit_object.hexsha = 'c1d322dfba0ed7a770d74074990ac51a9efedcd0'
        commit.repo_object.past_signoffs = [
            ['dco-signoffs',"I, personname hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: [personname@domain.com]\n\n11ac960e1070eacc2fe92ac9a3d1753400e1fd4b This is a commit".encode() ]
        ]

        self.assertFalse(commit.hasDCOPastSignoff(), "Commit message had a past signoff")

    def testDCOSignoffRequiredMergeCommit(self):
        commit = Commit(self._mock_commit_merge,self._mock_repo)

        self.assertFalse(commit.isDCOSignOffRequired(), "Merge commits don't require a DCO signoff")

    def testDCOSignoffRequiredNormalCommit(self):
        commit = Commit(self._mock_commit,self._mock_repo)

        self.assertTrue(commit.isDCOSignOffRequired(), "All non-merge commits require a DCO signoff")

    def testDCOSignoffCheckMergeCommit(self):
        commit = Commit(self._mock_commit_merge,self._mock_repo)
        commit.git_commit_object.message = "has no signoff"
        self.assertTrue(commit.checkDCOSignoff(), "Commit message didn't have a signoff, but is a merge commit so that's ok")
        
    def testDCOSignoffCheckNormalCommitNoSignoffPastSignoff(self):
        commit = Commit(self._mock_commit_merge,self._mock_repo)
        commit.git_commit_object.hexsha = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
        commit.repo_object.past_signoffs = [
            ['dco-signoffs',"I, personname hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: [personname@domain.com]\n\n11ac960e1070eacc2fe92ac9a3d1753400e1fd4b This is a commit".encode() ]
        ]
        commit.git_commit_object.message = "has no signoff"
        self.assertTrue(commit.checkDCOSignoff(), "Commit message didn't have a signoff, but it has a past DCO signoff so that's ok")

class TestOrg(unittest.TestCase):

    githubOrgRepos = [
        type("gh_repo",(object,),{
            "html_url": "https://github.com/testorg/repo1",
            "name":"repo1",
            "archived":False
            }),
        type("gh_repo",(object,),{
            "html_url": "https://github.com/testorg/repo2",
            "name":"repo2",
            "archived":False
            }),
        type("gh_repo",(object,),{
            "html_url": "https://github.com/testorg/repo3",
            "name":"repo3",
            "archived":True
            }),
            ]

    def testInitNoLoadRepos(self):
        org = Org("testorg",load_repos=False)

        self.assertEqual(org.repos,[])

    def testOrgTypeSetGithubNoTokenDefined(self):
        names_to_remove = {"GITHUB_TOKEN"}
        modified_environ = {
            k: v for k, v in os.environ.items() if k not in names_to_remove
        }
        with unittest.mock.patch.dict(os.environ, modified_environ, clear=True):
            self.assertRaisesRegex(Exception,'Github token',Org,'foo')

    @unittest.mock.patch.dict(os.environ,{'GITHUB_TOKEN':'test123'})
    @unittest.mock.patch.object(git.Repo,'clone_from')
    def testLoadOrgRepos(self,mock_method):
        with unittest.mock.patch.object(Org,'_getGithubReposForOrg',return_value=self.githubOrgRepos) as mock:
            org = Org("testorg")
       
            self.assertEqual(org.repos[0].name,"repo1")
            self.assertEqual(org.repos[1].name,"repo2")
            self.assertEqual(len(org.repos),2)

    @unittest.mock.patch.dict(os.environ,{'GITHUB_TOKEN':'test123'})
    @unittest.mock.patch.object(git.Repo,'clone_from')
    def testLoadOrgReposIgnoreRepo(self,mock_method):
        with unittest.mock.patch.object(Org,'_getGithubReposForOrg',return_value=self.githubOrgRepos) as mock:
            org = Org("testorg",ignore_repos=['repo1'])
       
            self.assertEqual(org.repos[0].name,"repo2")
            self.assertEqual(len(org.repos),1)
            
    @unittest.mock.patch.dict(os.environ,{'GITHUB_TOKEN':'test123'})
    @unittest.mock.patch.object(git.Repo,'clone_from')
    def testLoadOrgReposOnlyRepo(self,mock_method):
        with unittest.mock.patch.object(Org,'_getGithubReposForOrg',return_value=self.githubOrgRepos) as mock:
            org = Org("testorg",only_repos=['repo1'])
       
            self.assertEqual(org.repos[0].name,"repo1")
            self.assertEqual(len(org.repos),1)
    
    @unittest.mock.patch.dict(os.environ,{'GITHUB_TOKEN':'test123'})
    @unittest.mock.patch.object(git.Repo,'clone_from')
    def testLoadOrgReposIncludeArchives(self,mock_method):
        with unittest.mock.patch.object(Org,'_getGithubReposForOrg',return_value=self.githubOrgRepos) as mock:
            org = Org("testorg",skip_archived=False)
       
            self.assertEqual(org.repos[0].name,"repo1")
            self.assertEqual(org.repos[1].name,"repo2")
            self.assertEqual(org.repos[2].name,"repo3")
            self.assertEqual(len(org.repos),3)

if __name__ == '__main__':
    unittest.main()
