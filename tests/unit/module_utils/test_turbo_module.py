# -*- coding: utf-8 -*-
# Copyright 2020 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest
import ansible.module_utils.basic
from ansible_collections.cloud.common.plugins.module_utils.turbo.module import (
    collection_name,
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
    assert collection_name() == my_collection_name
