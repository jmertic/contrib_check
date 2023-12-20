#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import os
import git

import unittest
from unittest import mock
from unittest.mock import Mock
from unittest.mock import patch

from contrib_check.org import Org
from contrib_check.repo import Repo
from contrib_check.commit import Commit


class TestCommit(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self._mock_repo = Mock()
        self._mock_repo.heads = Mock()
        self._mock_repo.git_repo_object.head = Mock()
        self._mock_repo.git_repo_object.head.commit = Mock()
        data = [{"name": ".github/dco.yml"}]
        self._mock_repo.git_repo_object.head.commit.tree = {x['name']: x for x in data}
        self._mock_repo.git_repo_object.head.commit.tree[".github/dco.yml"] = Mock()
        self._mock_repo.git_repo_object.head.commit.tree[".github/dco.yml"].abspath = "foo"
        
        self._mock_commit_merge = Mock()
        self._mock_commit_merge.parents = [1,2,3]

        self._mock_commit = Mock()
        self._mock_commit.parents = [1]

    # test for not having a signoff
    def testHasNoDCOSignOff(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.message = "has no signoff"
            self.assertFalse(commit.hasDCOSignOff(), "Commit message didn't have a signoff")

    # test for having a signoff
    def testHasDCOSignOff(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.message = "has a signoff  Signed-off-by: John Mertic <jmertic@linuxfoundation.org>"
            self.assertTrue(commit.hasDCOSignOff(), "Commit message had a signoff")

    def testFoundPastDCOSignoff(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.hexsha = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
            commit.repo_object.past_signoffs = [
                "I, personname hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: [personname@domain.com]\n\n11ac960e1070eacc2fe92ac9a3d1753400e1fd4b This is a commit".encode() 
            ]

            self.assertTrue(commit.hasDCOPastSignoff(), "Commit message had a past signoff")

    def testFoundNoPastDCOSignoff(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.hexsha = 'c1d322dfba0ed7a770d74074990ac51a9efedcd0'
            commit.repo_object.past_signoffs = [
                "I, personname hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: [personname@domain.com]\n\n11ac960e1070eacc2fe92ac9a3d1753400e1fd4b This is a commit".encode() 
            ]

            self.assertFalse(commit.hasDCOPastSignoff(), "Commit message had a past signoff")

    def testDCOSignoffRequiredMergeCommit(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit_merge,self._mock_repo)

            self.assertFalse(commit.isDCOSignOffRequired(), "Merge commits don't require a DCO signoff")

    def testDCOSignoffRequiredNormalCommit(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)

            self.assertTrue(commit.isDCOSignOffRequired(), "All non-merge commits require a DCO signoff")

    def testDCOSignoffCheckMergeCommit(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit_merge,self._mock_repo)
            commit.git_commit_object.message = "has no signoff"
            self.assertTrue(commit.checkDCOSignoff(), "Commit message didn't have a signoff, but is a merge commit so that's ok")
        
    def testDCOSignoffCheckNormalCommitNoSignoffPastSignoff(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.hexsha = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
            commit.repo_object.past_signoffs = [
                "I, personname hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: [personname@domain.com]\n\n11ac960e1070eacc2fe92ac9a3d1753400e1fd4b This is a commit".encode() 
            ]
            commit.git_commit_object.message = "has no signoff"
            self.assertTrue(commit.checkDCOSignoff(), "Commit message didn't have a signoff, but it has a past DCO signoff so that's ok")

    def testDCOSignoffCheckNormalCommitNoSignoffHasRemediation(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.hexsha = '11ac960e1070eacc2fe92ac9a3d1753400e1fd4b'
            commit.git_commit_object.message = "has no signoff"
            commit.repo_object.past_signoffs = []
            commit.repo_object.git_repo_object.git.rev_parse = Mock(return_value='0e1fd4b')
            commit.remediations.append('0e1fd4b')
            self.assertTrue(commit.checkDCOSignoff(), "Commit message didn't have a signoff, but it has a remediation commit so that's ok")

    def testIsRemediationCommitIndividual(self):
        dcoConfig = '''
allowRemediationCommits:
  individual: true   
'''
        with patch('builtins.open', mock.mock_open(read_data=dcoConfig)) as m: 
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.message = '''
DCO Remediation Commit for lparadkar-rocket <lparadkar@rocketsoftware.com>

I, lparadkar-rocket <lparadkar@rocketsoftware.com>, hereby add my Signed-off-by to this commit: 41febb6
I, lparadkar-rocket <lparadkar@rocketsoftware.com>, hereby add my Signed-off-by to this commit: 41febb7
'''
            commit.git_commit_object.author = Mock()
            commit.git_commit_object.author.name = 'lparadkar-rocket'
            commit.git_commit_object.author.email = 'lparadkar@rocketsoftware.com'

            self.assertTrue(commit.isRemediationCommit())
            self.assertIn('41febb6',commit.remediations)
            self.assertIn('41febb7',commit.remediations)
    
    def testIsRemediationCommitThirdParty(self):
        dcoConfig = '''
allowRemediationCommits:
  thirdParty: true   
'''
        with patch('builtins.open', mock.mock_open(read_data=dcoConfig)) as m: 
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.git_commit_object.message = '''
Third-Party DCO Remediation Commit for Billy Bob Thorton <billybob@thorton.org>

On behalf of Billy Bob Thorton <billybob@thorton.org>, I, lparadkar-rocket <lparadkar@rocketsoftware.com>, hereby add my Signed-off-by to this commit: 41febb6
On behalf of Billy Bob Thorton <billybob@thorton.org>, I, lparadkar-rocket <lparadkar@rocketsoftware.com>, hereby add my Signed-off-by to this commit: 41febb7
'''
            commit.git_commit_object.author = Mock()
            commit.git_commit_object.author.name = 'lparadkar-rocket'
            commit.git_commit_object.author.email = 'lparadkar@rocketsoftware.com'

            self.assertTrue(commit.isRemediationCommit())
            self.assertIn('41febb6',commit.remediations)
            self.assertIn('41febb7',commit.remediations)
    
    def testHasRemediation(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.repo_object.git_repo_object.git.rev_parse = Mock(return_value='1234567')
            commit.remediations = ['1234567']

            self.assertTrue(commit.hasRemediation())

    def testHasNoRemediation(self):
        with patch('builtins.open', mock.mock_open(read_data="")) as m:
            commit = Commit(self._mock_commit,self._mock_repo)
            commit.repo_object.git_repo_object.git.rev_parse = Mock(return_value='1234567')
            commit.remediations = ['123i567']

            self.assertFalse(commit.hasRemediation())


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

    @classmethod
    def tearDownClass(cls):
        if os.path.exists("testorg-repo1.csv"):
            os.remove("testorg-repo1.csv")
        if os.path.exists("testorg-repo2.csv"):
            os.remove("testorg-repo2.csv")
        if os.path.exists("testorg-repo3.csv"):
            os.remove("testorg-repo3.csv")

    @unittest.mock.patch.dict(os.environ,{'GITHUB_TOKEN':'test123'})
    def testInitNoLoadRepos(self):
        org = Org("testorg",load_repos=False)

        self.assertEqual(org.repos,[])

    @unittest.mock.patch.dict(os.environ,{'GITHUB_TOKEN':'test123'})
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

class TestRepo(unittest.TestCase):

    @unittest.mock.patch.object(git.Repo,'clone_from')
    def testInitGithub(self,mock_method):
        repo = Repo("https://github.com/foo/bar")
        
        self.assertEqual(repo.name,"bar")
        self.assertEqual(repo.html_url,"https://github.com/foo/bar")
        self.assertEqual(repo.csv_filename,"foo-bar.csv")

    @unittest.mock.patch.object(git.Repo,'clone_from')
    def testInitLocal(self,mock_method):
        repo = Repo(".")
        
        self.assertEqual(repo.name,os.path.basename(os.path.realpath(".")))
        self.assertEqual(repo.html_url,"")
        self.assertEqual(repo.csv_filename,repo.name+".csv")

if __name__ == '__main__':
    unittest.main()
