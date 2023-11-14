# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# py38 only, See: https://github.com/PyCQA/pylint/issues/2976
from unittest.mock import Mock, ANY  # pylint: disable=syntax-error
import time
import pytest
import socket
import subprocess
import os
import ansible.module_utils.basic
from pathlib import Path
import sys
from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (
    get_collection_name_from_path,
    expand_argument_specs_aliases,
    prepare_args,
)
import ansible_collections.cloud.common.plugins.module_utils.turbo.common as turbo_common


@pytest.mark.parametrize(
    "my_module_path,my_collection_name",
    [
        (
            "/tmp/ansible_vmware.vmware_rest.vcenter_vm_info_payload_548h2lev/ansible_vmware.vmware_rest.vcenter_vm_info_payload.zip/ansible/module_utils",
            "vmware.vmware_rest",
        )
    ],
)
def test_collection_name(monkeypatch, my_module_path, my_collection_name):
    def mocked_func():
        return my_module_path

    monkeypatch.setattr(ansible.module_utils.basic, "get_module_path", mocked_func)
    assert get_collection_name_from_path() == my_collection_name


class MockPopen:
    def __init__(self):
        self.returncode = 0

    @staticmethod
    def communicate():
        return b"output log", b"error log"


def mocked_Popen(*args, **kwargs):
    return MockPopen()


@pytest.fixture
def test_start_daemon_from_module(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", mocked_Popen)
    turbo_socket = turbo_common.AnsibleTurboSocket(socket_path="/aa")
    running, error = turbo_socket.start_server()
    assert running
    mocked_Popen.assert_called_once_with(
        [
            ANY,
            "-m",
            "ansible_collections.cloud.common.plugins.module_utils.turbo.server",
            "--fork",
            "--socket-path",
            "/aa",
        ],
        env=ANY,
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@pytest.fixture
def test_start_daemon_from_lookup(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", mocked_Popen)
    turbo_socket = turbo_common.AnsibleTurboSocket(
        socket_path="/aa", plugin="lookup", ttl=150
    )
    running, error = turbo_socket.start_server()
    assert running
    mocked_Popen.assert_called_once_with(
        [
            ANY,
            os.path.join(os.path.dirname(turbo_common.__file__), "server.py"),
            "--fork",
            "--socket-path",
            "/aa",
            "--ttl",
            "150",
        ],
        env=ANY,
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_start_daemon_with_no_mock(tmp_path):
    # This is an ugly fix to get this to pass in CI
    p = Path.cwd().parents
    sys.path.insert(0, str(p[2]))
    my_socket = tmp_path / "socket"
    turbo_socket = turbo_common.AnsibleTurboSocket(socket_path=str(my_socket), ttl=1)
    assert turbo_socket.start_server()
    time.sleep(0.5)
    assert my_socket.is_socket()
    time.sleep(0.8)
    assert not my_socket.exists()


def test_connect(monkeypatch):
    mocked_socket = Mock()
    monkeypatch.setattr(socket, "socket", mocked_socket)
    turbo_socket = turbo_common.AnsibleTurboSocket(socket_path="/nowhere")
    assert turbo_socket.bind()
    mocked_socket.connect_assert_called_once_with("/nowhere")


def test_expand_argument_specs_aliases():
    argspec = {"foo": {"type": int, "aliases": ["bar"]}}
    assert expand_argument_specs_aliases(argspec) == {
        "foo": {"type": int, "aliases": ["bar"]},
        "bar": {"type": int, "aliases": ["bar"]},
    }


def test_prepare_args():
    argspec = {"foo": {"type": int}}
    params = {"foo": 1}
    assert prepare_args(argspec, params) == {"ANSIBLE_MODULE_ARGS": {"foo": 1}}


def test_prepare_args_ignore_none():
    argspec = {"foo": {"type": int}}
    params = {"foo": None}
    assert prepare_args(argspec, params) == {"ANSIBLE_MODULE_ARGS": {}}


def test_prepare_args_subkey_freeform():
    argspec = {"foo": {"type": dict, "default": {}}}
    params = {"foo": {"bar": 1}}
    assert prepare_args(argspec, params) == {"ANSIBLE_MODULE_ARGS": {"foo": {"bar": 1}}}


def test_prepare_args_subkey_with_default():
    argspec = {"foo": {"bar": {"default": 1}}}
    params = {"foo": {"bar": 1}}
    assert prepare_args(argspec, params) == {"ANSIBLE_MODULE_ARGS": {"foo": {}}}


def test_prepare_args_dedup_aliases():
    argspec = {"foo": {"aliases": ["bar"], "type": int}}
    params = {"foo": 1, "bar": 1}
    assert prepare_args(argspec, params) == {"ANSIBLE_MODULE_ARGS": {"foo": 1}}


def test_prepare_args_with_aliases():
    argspec = {"foo": {"aliases": ["bar"], "type": int}}
    params = {"foo": 1}
    assert prepare_args(argspec, params) == {"ANSIBLE_MODULE_ARGS": {"foo": 1}}
