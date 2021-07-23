import json
import os
import sys

import ansible.module_utils.basic
from .exceptions import (
    EmbeddedModuleSuccess,
    EmbeddedModuleFailure,
)
import ansible_collections.cloud.common.plugins.module_utils.turbo.common

if False:  # pylint: disable=using-constant-test
    from .server import please_include_me

    # This is a trick to be sure server.py is embedded in the Ansiblez
    # zip archive.🥷
    please_include_me


def get_collection_name_from_path():
    module_path = ansible.module_utils.basic.get_module_path()

    ansiblez = module_path.split("/")[-3]
    if ansiblez.startswith("ansible_") and ansiblez.endswith(".zip"):
        return ".".join(ansiblez[8:].split(".")[:2])


class AnsibleTurboModule(ansible.module_utils.basic.AnsibleModule):
    embedded_in_server = False
    collection_name = None

    def __init__(self, *args, **kwargs):
        self.embedded_in_server = sys.argv[0].endswith("/server.py")
        self.collection_name = (
            AnsibleTurboModule.collection_name or get_collection_name_from_path()
        )
        ansible.module_utils.basic.AnsibleModule.__init__(
            self, *args, bypass_checks=not self.embedded_in_server, **kwargs
        )
        self._running = None
        if not self.embedded_in_server:
            self.run_on_daemon()

    def socket_path(self):
        return (
            os.environ["HOME"]
            + f"/.ansible/tmp/turbo_mode.{self.collection_name}.socket"
        )

    def _get_argument_specs(self):
        """Returns a dict of accepted argument that includes the aliases"""
        argument_specs = {}
        for k, v in self.argument_spec.items():
            for alias in [k] + v.get("aliases", []):
                argument_specs[alias] = v
        return argument_specs

    def _prepare_args(self):
        argument_specs = self._get_argument_specs()

        def _keep_value(v, argument_specs, key, subkey=None):
            if v is None:  # cannot be a valide parameter
                return False
            if key not in argument_specs:  # should never happen
                return
            if not subkey:  # level 1 parameter
                return v != argument_specs[key].get("default")
            elif subkey not in argument_specs[key]:  # Freeform
                return True
            elif isinstance(argument_specs[key][subkey], dict):
                return v != argument_specs[key][subkey].get("default")
            else:  # should never happen
                return True

        new_params = {}
        for k, v in self.params.items():
            if not _keep_value(v, argument_specs, k):
                continue

            if isinstance(v, dict):
                new_params[k] = {
                    i: j for i, j in v.items() if _keep_value(j, argument_specs, k, i)
                }
            else:
                new_params[k] = v
        args = {"ANSIBLE_MODULE_ARGS": new_params}
        for k in ansible.module_utils.basic.PASS_VARS:
            attribute = ansible.module_utils.basic.PASS_VARS[k][0]
            if not hasattr(self, attribute):
                continue
            v = getattr(self, attribute)
            if isinstance(v, int) or isinstance(v, bool) or isinstance(v, str):
                args["ANSIBLE_MODULE_ARGS"][f"_ansible_{k}"] = v
        return args

    def run_on_daemon(self):
        result = dict(changed=False, original_message="", message="")
        ttl = os.environ.get("ANSIBLE_TURBO_LOOKUP_TTL", None)
        with ansible_collections.cloud.common.plugins.module_utils.turbo.common.connect(
            socket_path=self.socket_path(), ttl=ttl
        ) as turbo_socket:
            ansiblez_path = sys.path[0]
            args = self._prepare_args()
            data = [
                ansiblez_path,
                json.dumps(args),
            ]
            content = json.dumps(data).encode()
            result = turbo_socket.communicate(content)
        self.exit_json(**result)

    def exit_json(self, **kwargs):
        if not self.embedded_in_server:
            super().exit_json(**kwargs)
        else:
            self.do_cleanup_files()
            raise EmbeddedModuleSuccess(**kwargs)

    def fail_json(self, *args, **kwargs):
        if not self.embedded_in_server:
            super().fail_json(**kwargs)
        else:
            self.do_cleanup_files()
            raise EmbeddedModuleFailure(*args, **kwargs)
