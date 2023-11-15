# -*- coding: utf-8 -*-
# Copyright 2021 XLAB Steampunk
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json

import pytest
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes


@pytest.fixture
def set_module_args(monkeypatch):
    def wrapper(args=None):
        module_args = dict(ANSIBLE_MODULE_ARGS=args or {})
        monkeypatch.setattr(basic, "_ANSIBLE_ARGS", to_bytes(json.dumps(module_args)))

    return wrapper
