import json
import os
import socket
import sys
import time
import subprocess
import pickle

from ansible.plugins.lookup import LookupBase
from ansible.module_utils.six import string_types

from .exceptions import EmbeddedModuleUnexpectedFailure


def start_daemon(socket_path, server_py, ttl=None):

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
            server_py,
        ]
        + parameters,
        env=os.environ,
        close_fds=True,
    )
    p.communicate()
    return p.pid


def connect(socket_path, server_py, ttl=None):
    running = False
    _socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    for attempt in range(100, -1, -1):
        try:
            _socket.connect(socket_path)
            return _socket
        except (ConnectionRefusedError, FileNotFoundError):
            if not running:
                running = start_daemon(socket_path, server_py, ttl)
            if attempt == 0:
                raise
        time.sleep(0.01)


def get_server_ttl(variables):
    # trying to retrieve first TTL from environment variable
    ttl = os.environ.get("ANSIBLE_TURBO_LOOKUP_TTL", None)
    if ttl is not None:
        return ttl
    # Read TTL from ansible environment
    for env_var in variables.get("environment", []):
        value = env_var.get("ANSIBLE_TURBO_LOOKUP_TTL", None)
        test_var_int = [
            isinstance(value, string_types) and value.isnumeric(),
            isinstance(value, int),
        ]
        if value is not None and any(test_var_int):
            ttl = value
    return ttl


class TurboLookupBase(LookupBase):
    def run_on_daemon(self, terms, variables=None, **kwargs):
        if os.path.isfile(self.server_path):
            self.ttl = get_server_ttl(variables)
            return self.execute(terms=terms, variables=variables, **kwargs)
        # run standard lookup (turbo mode not enabled)
        return self._run(terms=terms, variables=variables, **kwargs)

    @property
    def server_path(self):
        if not hasattr(self, "__server_path"):
            parent_dir = os.path.dirname(__file__)
            self.__server_path = os.path.join(parent_dir, "server.py")
        return self.__server_path

    @property
    def socket_path(self):
        if not hasattr(self, "__socket_path"):
            """
            Input:
                _load_name: ansible_collections.cloud.common.plugins.lookup.turbo_random_lookup
            Output:
                __socket_path: {HOME}/.ansible/tmp/turbo_lookup_cloud.common.socket
            this will allow to have one socket per collection
            """
            name = self._load_name
            ansible_collections = "ansible_collections."
            if name.startswith(ansible_collections):
                name = name.replace(ansible_collections, "", 1)
                lookup_plugins = ".plugins.lookup."
                idx = name.find(lookup_plugins)
                if idx != -1:
                    name = name[:idx]
            self.__socket_path = (
                os.environ["HOME"] + f"/.ansible/tmp/turbo_mode.{name}.socket"
            )
        return self.__socket_path

    def execute(self, terms, variables=None, **kwargs):
        _socket = connect(self.socket_path, self.server_path, self.ttl)
        content = (self._load_name, terms, variables, kwargs)
        encoded_data = pickle.dumps(("lookup", content))
        _socket.sendall(encoded_data)
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
            (result, errors) = json.loads(raw_answer.decode())
            if errors:
                raise EmbeddedModuleUnexpectedFailure(errors)
        except json.decoder.JSONDecodeError:
            raise EmbeddedModuleUnexpectedFailure(
                f"Cannot decode lookup answer: {raw_answer}"
            )
        return result
