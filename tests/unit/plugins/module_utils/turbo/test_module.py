# -*- coding: utf-8 -*-
# Copyright 2021 XLAB Steampunk
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import sys

import pytest
from ansible.module_utils import basic
from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (
    AnsibleTurboModule,
)


def _patch_globals(monkeypatch):
    # Patch sys.argv so that module does not try to spin up the server on
    # initialization. The purpose is to make sure AnsibleTurboModule.embedded_in_server
    # is set to True.
    monkeypatch.setattr(sys, "argv", ["something/that/ends/on/server.py"])

    # Collection name detection will fail in unit tests, so we patch it here directly
    # and bypass the detection process.
    monkeypatch.setattr(AnsibleTurboModule, "collection_name", "namespace.name")

    # Patch the ansible profile global var, since it is not set when running unit test. This
    # var only exists for ansible 2.19 and above
    try:
        monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy")
    except AttributeError:
        pass


def test_module_socket_path_remote_tmp_not_set(monkeypatch, set_module_args):
    _patch_globals(monkeypatch)
    set_module_args()
    module = AnsibleTurboModule(argument_spec={})
    path = module.socket_path()

    # We cannot know what tmp dir python uses, but we do know that it is a full path
    # that ends with deterministc suffix.
    assert path.startswith("/")
    assert path.endswith("/turbo_mode.namespace.name.socket")


@pytest.mark.parametrize("tmp_path", ["/tmp", "/tmp/"])
def test_module_socket_path_from_remote_tmp(monkeypatch, set_module_args, tmp_path):
    _patch_globals(monkeypatch)
    set_module_args(dict(_ansible_remote_tmp=tmp_path))
    module = AnsibleTurboModule(argument_spec={})

    assert module.socket_path() == "/tmp/turbo_mode.namespace.name.socket"


@pytest.mark.parametrize(
    "tmp_path", ["/t/$MY_VAR", "/t/${MY_VAR}", "/t/$MY_VAR/", "/t/${MY_VAR}/"]
)
def test_module_socket_path_env_vars_in_remote_tmp(
    monkeypatch, set_module_args, tmp_path
):
    _patch_globals(monkeypatch)
    set_module_args(dict(_ansible_remote_tmp=tmp_path))
    monkeypatch.setenv("MY_VAR", "my_var_value")
    module = AnsibleTurboModule(argument_spec={})

    assert module.socket_path() == "/t/my_var_value/turbo_mode.namespace.name.socket"
