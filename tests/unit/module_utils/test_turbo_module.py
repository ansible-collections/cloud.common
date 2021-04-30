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
import ansible.module_utils.basic
from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (
    get_collection_name_from_path,
    connect,
    start_daemon,
)


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


def test_start_daemon(monkeypatch):
    mocked_Popen = Mock()
    monkeypatch.setattr(subprocess, "Popen", mocked_Popen)
    assert start_daemon("/aa")
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
    )


def test_start_daemon_with_no_mock(tmp_path):
    my_socket = tmp_path / "socket"
    assert start_daemon(socket_path=str(my_socket), ttl=1)
    time.sleep(0.5)
    assert my_socket.is_socket()
    time.sleep(0.8)
    assert not my_socket.exists()


def test_connect(monkeypatch):
    mocked_socket = Mock()
    monkeypatch.setattr(socket, "socket", mocked_socket)
    assert connect("/nowhere")
    mocked_socket.connect_assert_called_once_with("/nowhere")
