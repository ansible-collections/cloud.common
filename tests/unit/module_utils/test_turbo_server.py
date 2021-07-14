# -*- coding: utf-8 -*-
# Copyright 2021 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os

from ansible_collections.cloud.common.plugins.module_utils.turbo.server import wrap_env


def test_wrap_env():
    original_env = os.environ.copy()
    assert os.environ.get("TEST_VAR") is None
    with wrap_env({"TEST_VAR": "FOO"}):
        assert os.environ.get("TEST_VAR") == "FOO"
    assert os.environ.get("TEST_VAR") is None
    assert original_env == os.environ
