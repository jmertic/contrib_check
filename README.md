# Contribution Checker

Checks contributions in a repo or a GitHub org for:

- DCO signoffs ( https://developercertificate.org )

Refactor of previous [dco-org-check](https://github.com/jmertic/dco-org-check) script for extensibility.

The script will produce a CSV file named after the repo with any commits matching a check, and for DCO signoffs will produce the commit message to use for remediation commits.

```
DCO Remediation Commit for John Doe <john.doe@foo.com>        

I, John Doe <john.doe@foo.com>, hereby add my Signed-off-by to this commit: 845f7fc    
I, John Doe <john.doe@foo.com, hereby add my Signed-off-by to this commit: 45248d3
```

You can do any checkin to the repository to with that in the commit message to provide the remediation commit.

## Installation

```bash
pipx install git+https://github.com/jmertic/contrib_check.git
```

## Usage

```bash
usage: contrib-check [-h] (--repo REPO | --org ORG) [-o OUTPUT_DIR] [--org-type ORG_TYPE] [--dco-skip] [--dco-allow-individual-remediation-commits]
                     [--dco-allow-thirdparty-remediation-commits] [--dco-signoff-dirs DCO_SIGNOFF_DIRS] [--dco-start-date DCO_START_DATE]
                     [--dco-start-commit DCO_START_COMMIT] [--only-repos ONLY_REPOS | --ignore-repos IGNORE_REPOS] [--skip-archived-repos]
                     [-l {debug,info,warning,error,critical}] [--logfile LOGFILE]

Scan a single repo or organization for various contribution checks ( such as DCO )

options:
  -h, --help            show this help message and exit
  --repo REPO           URL or path to the repo to search (default: None)
  --org ORG             URL to GitHub org to search (default: None)
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Output directory (default: /Users/johnmertic/Code/contrib_check)
  --org-type ORG_TYPE   Type of Org (default: github)
  --dco-skip            Skips DCO checks (default: False)
  --dco-allow-individual-remediation-commits
                        Allow individual remediation commits for DCO signoffs (only needed if not enabled in dco.yml in the repo) (default: False)
  --dco-allow-thirdparty-remediation-commits
                        Allow third party remediation commits for DCO signoffs (only needed if not enabled in dco.yml in the repo) (default: False)
  --dco-signoff-dirs DCO_SIGNOFF_DIRS
                        List of directory names, comma delimited, where past signoffs could be in the repo (default: dco-signoffs,dco_signoffs)
  --dco-start-date DCO_START_DATE
                        Start checking for DCO signoffs after the provided date (ISO format or relative date, e.g. '2 weeks ago') (default: None)
  --dco-start-commit DCO_START_COMMIT
                        Start checking for DCO signoffs after the provided commit hash (default: None)
  --only-repos ONLY_REPOS
                        When specifying an org, only include the comma delimited list of repos (default: None)
  --ignore-repos IGNORE_REPOS
                        When specifying an org, do not include the comma delimited list of repos (default: None)
  --skip-archived-repos
                        Skip repos marked as Archived (default: False)
  -l {debug,info,warning,error,critical}, --log {debug,info,warning,error,critical}
                        Logging level (default: error)
  --logfile LOGFILE     Name for the log file (default: debug.log)
```

## Contributing

Feel free to send [issues](/issues) or [pull requests](/pulls) ( with a DCO signoff of course :-) ) in accordance with the [contribution guidelines](CONTRIBUTING.md)

For more checks to add, note the scope of this tool is scanning contributions to a repository.

SPDX-License-Identifier: Apache-2.0
