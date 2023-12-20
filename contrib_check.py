#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import shutil
from argparse import ArgumentParser,FileType
from datetime import datetime

# third party modules
import yaml

from contrib_check.repo import Repo
from contrib_check.org import Org

def main():

    startTime = datetime.now()

    parser = ArgumentParser(description="Scan a single repo or organization for various contribution checks ( such as DCO )")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--config", dest="configfile", type=FileType('r'), help="name of YAML config file")
    group.add_argument("--repo", dest="repo", help="URL or path to the repo to search")
    group.add_argument("--org", dest="org", help="URL to GitHub org to search")
    parser.add_argument("--dco", dest="dco", help="Perform a DCO check (defaults to true)", default=True)
    args = parser.parse_args()

    config = {}
    if args.configfile:
        config = yaml.safe_load(args.configfile)
        if 'dco' in config and 'prior_commits' in config['dco'] and 'directory' in config['dco']['prior_commits']:
            dco_prior_commits_directory = config['dco']['prior_commits']['directory'] 
            shutil.rmtree(dco_prior_commits_directory,1)
        if 'repo' in config:
            args.repo = config['repo']
        elif 'org' in config:
            args.org = config['org']['name']
   
    repos = []
    if args.org:
        orgObj = Org(args.org,load_repos=False)
        if 'type' in config['org']:
            orgObj.org_type=config['org']['type']
        if 'ignore_repos' in config['org']:
            orgObj.ignore_repos = config['org']['ignore_repos']
        if 'only_repos' in config['org']:
            orgObj.only_repos=config['org']['only_repos']
        if 'skip_archived' in config['org']:
            orgObj.skip_archived=config['org']['skip_archived']
        repos = orgObj.reloadRepos()

    if args.repo:
        repos = [Repo(args.repo)]

    for repoObj in repos:
        print("Searching repo {}...".format(repoObj.name))
        if 'dco' in config or args.dco:
            if 'dco' in config and 'prior_commits_directory' in config['dco']:
                repoObj.prior_commits_dir = config['dco']['prior_commits_directory']
            if 'dco' in config and 'signoff_dirs' in config['dco']:
                repoObj.loadPastSignoffs(config['dco']['signoff_dirs'])
            else:
                repoObj.loadPastSignoffs()
        repoObj.scan()
        print(repoObj.remediations)

    print("This took "+str(datetime.now() - startTime))

if __name__ == '__main__':
    main()
