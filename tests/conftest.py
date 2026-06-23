#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import logging
import pytest

logger = logging.getLogger(__name__)

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Executes automatically right before any test begins running.

    'item' contains all the metadata about the test being executed.
    """
    # item.nodeid looks like: tests/test_repo.py::TestRepoInitGithub::test_csv_filename
    logger.info(f"============ STARTING TEST: {item.nodeid} ============")
