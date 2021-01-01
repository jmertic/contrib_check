# Contribution checker

Checks contributions in a repo or a GitHub org for:

- DCO signoffs ( https://developercertificate.org )

Refactor of previous [dco-org-check](https://github.com/jmertic/dco-org-check) script for extensibility.

## Installation

```
git clone https://github.com/jmertic/contrib_check
cd contrib_check
chmod +x contrib_check.py
pip install -r requirements.txt
```

## Usage

```
usage: contrib_check.py [-h] [-c CONFIGFILE]

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIGFILE, --config CONFIGFILE
                        name of YAML config file (defaults to
                        dco_org_check.yaml)
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
    prior-commits:
      # directory where to store the prior commits files
      directory: dco-signoffs
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
