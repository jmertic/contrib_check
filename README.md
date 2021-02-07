# Contribution checker

Checks contributions in a repo or a GitHub org for:

- DCO signoffs ( https://developercertificate.org )

Refactor of previous [dco-org-check](https://github.com/jmertic/dco-org-check) script for extensibility.

The script will produce a CSV file named after the repo with any commits matching a check, and for DCO signoffs will produce a file similar to the below that can be checked into the repository and used for remediation...

```
I, John Doe hereby sign-off-by all of my past commits to this repo subject to the Developer Certificate of Origin (DCO), Version 1.1. In the past I have used emails: john.doe@foo.com

4f93aecac9b1a64331148cd496d0ee54584a1553 Commit 1
538c1d602cc6f59e7b600f49889069a4caac7959 Commit 2
9e57035ef29319fc44a7d167e7896bc144e80b10 Commit 3
```

## Installation

```
git clone https://github.com/jmertic/contrib_check
cd contrib_check
chmod +x contrib_check.py
pip install -r requirements.txt
```

## Usage

```
usage: contrib_check.py [-h] (-c CONFIGFILE | --repo REPO | --org ORG) [--dco DCO]

Scan a single repo or organization for various contribution checks ( such as DCO )

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIGFILE, --config CONFIGFILE
                        name of YAML config file
  --repo REPO           URL or path to the repo to search
  --org ORG             URL to GitHub org to search
  --dco DCO             Perform a DCO check (defaults to true)
```

### Config file options ( set argument is the default if not specified )

```yaml
# Path or URL to the repo 
repo: 
# set if scanning an org
org:
  # org type
  type: github
  # name
  name: 
  # list of repos to ignore when scanning
  ignore_repos:
    - repo1
    - repo2
    - ...
  # list of repos to only look at when scanning
  only_repos:
    - repo1
    - repo2
    - ...
# checks to run
checks:
  # set if dco
  dco:
    # list of directory names where previous commit signoffs are in the repo
    signoff_dirs:
      - dco-signoffs
    # set if you want to have the script create the previous commits signoff files
    prior-commits-directory: dco-signoffs
```

## Contributing

Feel free to send [issues](/issues) or [pull requests](/pulls) ( with a DCO signoff of course :-) ) in accordance with the [contribution guidelines](CONTRIBUTING.md)

For more checks to add, note the scope of this tool is scanning contributions to a repository. 

## Useful tools to make doing DCO signoffs easier

There are a number of great tools out there to manage DCO signoffs for developers to make it much easier to do signoffs.

- DCO command line tool, which let's you do a single signoff for an entire repo ( https://github.com/coderanger/dco )
- GitHub UI integrations for adding the signoff automatically ( https://github.com/scottrigby/dco-gh-ui )
  - Chrome - https://chrome.google.com/webstore/detail/dco-github-ui/onhgmjhnaeipfgacbglaphlmllkpoijo
  - Firefox - https://addons.mozilla.org/en-US/firefox/addon/scott-rigby/?src=search

SPDX-License-Identifier: Apache-2.0
