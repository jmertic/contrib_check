#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import shutil
from argparse import ArgumentParser, FileType, ArgumentDefaultsHelpFormatter
from datetime import datetime
import logging
import sys
from pathlib import Path

# third party modules
import yaml
from contrib_check.repo import Repo
from contrib_check.org import Org

def main():
    startTime = datetime.now()

    parser = ArgumentParser(
            description="Scan a single repo or organization for various contribution checks ( such as DCO )",
            formatter_class=ArgumentDefaultsHelpFormatter
            )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", dest="repo", help="URL or path to the repo to search")
    group.add_argument("--org", dest="org", help="URL to GitHub org to search")
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Output directory"
    )
    parser.add_argument("--org-type", default="github", help="Type of Org")
    parser.add_argument("--dco-skip", action="store_true", help="Skips DCO checks")
    parser.add_argument("--dco-allow-individual-remediation-commits",
                        action="store_true",
                        help="Allow individual remediation commits for DCO signoffs (only needed if not enabled in dco.yml in the repo)")
    parser.add_argument("--dco-allow-thirdparty-remediation-commits",
                        action="store_true",
                        help="Allow third party remediation commits for DCO signoffs (only needed if not enabled in dco.yml in the repo)")
    parser.add_argument("--dco-signoff-dirs",
                        help="List of directory names, comma delimited, where past signoffs could be in the repo",
                        default="dco-signoffs,dco_signoffs")
    parser.add_argument("--dco-start-date",
                        help="Start checking for DCO signoffs after the provided date (ISO format or relative date, e.g. '2 weeks ago')")
    parser.add_argument("--dco-start-commit",
                        help="Start checking for DCO signoffs after the provided commit hash")
    org_group = parser.add_mutually_exclusive_group()
    org_group.add_argument("--only-repos",
                           help="When specifying an org, only include the comma delimited list of repos")
    org_group.add_argument("--ignore-repos",
                           help="When specifying an org, do not include the comma delimited list of repos")
    parser.add_argument("--skip-archived-repos",
                        action="store_true",
                        help="Skip repos marked as Archived")
    parser.add_argument("-l", "--log", dest="loglevel", default="error",
                        choices=['debug', 'info', 'warning', 'error', 'critical'], help="Logging level")
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

    repos = []
    if args.org:
        repos = Org(
                org_name = args.org,
                org_type = args.org_type,
                only_repos = args.only_repos,
                ignore_repos = args.ignore_repos,
                skip_archived = args.skip_archived_repos,
                load_repos = False
                ).repos

    if args.repo:
        repos = [Repo(args.repo)]

    for repoObj in repos:
        if not args.dco-skip:
            logging.getLogger().info(f"Searching repo {repoObj.name} for DCO signoffs")
            repoObj.load_past_signoffs(args.dco-signoff-dirs)
            repoObj.scan(since_date=args.dco-start-date,since_commit=args.dco-start-commit,output_dir=args.output_dir)

    logging.getLogger().info("This took {} seconds".format(str(datetime.now() - startTime)))
