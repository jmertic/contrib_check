#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import shutil
from argparse import ArgumentParser, FileType
from datetime import datetime
import logging
import sys

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
    parser.add_argument("--dco-allow-individual-remediation-commits",
                        dest="dco-allow-individual-remediation-commits",
                        help="Allow individual remediation commits for DCO signoffs (only needed if not enabled in dco.yml in the repo)",
                        default=False)
    parser.add_argument("--dco-allow-thirdparty-remediation-commits",
                        dest="dco-allow-thirdparty-remediation-commits",
                        help="Allow third party remediation commits for DCO signoffs (only needed if not enabled in dco.yml in the repo)",
                        default=False)
    parser.add_argument("--dco-allow-dcosignoffs",
                        dest="dco-allow-dcosignoffs",
                        help="Allow reading and writing legacy DCO Signoff files")
    parser.add_argument("-l", "--log", dest="loglevel", default="error",
                        choices=['debug', 'info', 'warning', 'error', 'critical'], help="logging level")
    parser.add_argument("--logfile", default='debug.log', help="Name for the log file")

    args = parser.parse_args()

    levels = {
        'critical': logging.CRITICAL,   # errors that mean an immediate stop
        'error': logging.ERROR,         # general errors that will effect the output
        'warn': logging.WARNING,        # errors that can be caught and corrected
        'warning': logging.WARNING,
        'info': logging.INFO,           # infomational messages
        'debug': logging.DEBUG          # messages to help debug things misbehaving ;-)
    }
    handlers = [logging.FileHandler(args.logfile,mode="w")]
    handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=levels.get(args.loglevel.lower()),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )

    config = {}
    if args.configfile:
        config = yaml.safe_load(args.configfile)

        if 'dco' in config and 'prior_commits' in config['dco'] and 'directory' in config['dco']['prior_commits']:
            dco_prior_commits_directory = config['dco']['prior_commits']['directory']
            shutil.rmtree(dco_prior_commits_directory, 1)

        if 'repo' in config:
            args.repo = config['repo']
        elif 'org' in config:
            args.org = config['org']['name']

    repos = []
    if args.org:
        orgObj = Org(args.org, load_repos=False)
        if 'type' in config['org']:
            orgObj.org_type = config['org']['type']
        if 'ignore_repos' in config['org']:
            orgObj.ignore_repos = config['org']['ignore_repos']
        if 'only_repos' in config['org']:
            orgObj.only_repos = config['org']['only_repos']
        if 'skip_archived' in config['org']:
            orgObj.skip_archived = config['org']['skip_archived']
        repos = orgObj.reload_repos()

    if args.repo:
        repos = [Repo(args.repo)]

    for repoObj in repos:
        logging.getLogger().info(f"Searching repo {repoObj.name}")
        if 'dco' in config or args.dco:
            if 'dco' in config and 'prior_commits_directory' in config['dco']:
                repoObj.prior_commits_dir = config['dco']['prior_commits_directory']
            if 'dco' in config and 'signoff_dirs' in config['dco']:
                repoObj.load_past_signoffs(config['dco']['signoff_dirs'])
            else:
                repoObj.load_past_signoffs()
            repoObj.scan()

    logging.getLogger().info("This took {} seconds".format(str(datetime.now() - startTime)))
