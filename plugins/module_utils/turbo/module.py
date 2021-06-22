import json
import os
import socket
import sys
import time

import ansible.module_utils.basic
from .exceptions import (
    EmbeddedModuleSuccess,
    EmbeddedModuleFailure,
    EmbeddedModuleUnexpectedFailure,
)

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


def connect(socket_path):
    running = False
    _socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    for attempt in range(100, -1, -1):
        try:
            _socket.connect(socket_path)
            return _socket
        except (ConnectionRefusedError, FileNotFoundError):
            if not running:
                running = start_daemon(socket_path=socket_path)
            if attempt == 0:
                raise
        time.sleep(0.01)


def start_daemon(socket_path, ttl=None):
    ansiblez_path = sys.path[0]
    env = os.environ
    env.update({"PYTHONPATH": ansiblez_path})
    import subprocess

    parameters = [
        "--fork",
        "--socket-path",
        socket_path,
    ]

    if ttl:
        parameters += ["--ttl", str(ttl)]

    p = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ansible_collections.cloud.common.plugins.module_utils.turbo.server",
        ]
        + parameters,
        env=env,
        close_fds=True,
    )
    p.communicate()
    return p.pid


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
            if not hasattr(self, k):
                continue
            v = getattr(self, k)
            if isinstance(v, int) or isinstance(v, bool) or isinstance(v, str):
                args["ANSIBLE_MODULE_ARGS"][f"_ansible_{k}"] = v
        return args

    def run_on_daemon(self):
        _socket = connect(socket_path=self.socket_path())
        result = dict(changed=False, original_message="", message="")
        ansiblez_path = sys.path[0]
        args = self._prepare_args()
        data = [
            ansiblez_path,
            json.dumps(args),
        ]
        _socket.sendall(json.dumps(data).encode())
        _socket.shutdown(socket.SHUT_WR)
        raw_answer = b""
        while True:
            b = _socket.recv((1024 * 1024))
            if not b:
                break
            raw_answer += b
            time.sleep(0.01)
        _socket.close()
        try:
            result = json.loads(raw_answer.decode())
        except json.decoder.JSONDecodeError:
            raise EmbeddedModuleUnexpectedFailure(
                f"Cannot decode module answer: {raw_answer}"
            )
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
