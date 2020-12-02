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


def collection_name():
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._socket_path = (
            os.environ["HOME"] + f"/.ansible/tmp/turbo_mode.{collection_name()}.socket"
        )
        self._running = None
        self.embedded_in_server = sys.argv[0].endswith("/server.py")
        if not self.embedded_in_server:
            self.run_on_daemon()

    def run_on_daemon(self):
        _socket = connect(socket_path=self._socket_path)
        result = dict(changed=False, original_message="", message="")
        ansiblez_path = sys.path[0]
        args = {
            "ANSIBLE_MODULE_ARGS": {
                k: v for k, v in self.params.items() if v is not None
            }
        }
        for k in ansible.module_utils.basic.PASS_VARS:
            if not hasattr(self, k):
                continue
            v = getattr(self, k)
            if isinstance(v, int) or isinstance(v, bool) or isinstance(v, str):
                args["ANSIBLE_MODULE_ARGS"][f"_ansible_{k}"] = v
        data = [
            ansiblez_path,
            json.dumps(args),
        ]
        _socket.send(json.dumps(data).encode())
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
