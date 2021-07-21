import os
import socket
import sys
import time
import subprocess
import pickle
from contextlib import contextmanager
import json

from .exceptions import (
    EmbeddedModuleUnexpectedFailure,
)


class AnsibleTurboSocket:
    def __init__(self, socket_path, ttl=None, plugin="module"):
        self._socket_path = socket_path
        self._ttl = ttl
        self._plugin = plugin
        self._socket = None

    def bind(self):
        running = False
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        for attempt in range(100, -1, -1):
            try:
                self._socket.connect(self._socket_path)
                return True
            except (ConnectionRefusedError, FileNotFoundError):
                if not running:
                    running = self.start_server()
                if attempt == 0:
                    raise
            time.sleep(0.01)

    def start_server(self):
        env = os.environ
        parameters = [
            "--fork",
            "--socket-path",
            self._socket_path,
        ]

        if self._ttl:
            parameters += ["--ttl", str(self._ttl)]

        command = [sys.executable]
        if self._plugin == "module":
            ansiblez_path = sys.path[0]
            env.update({"PYTHONPATH": ansiblez_path})
            command += [
                "-m",
                "ansible_collections.cloud.common.plugins.module_utils.turbo.server",
            ]
        else:
            parent_dir = os.path.dirname(__file__)
            server_path = os.path.join(parent_dir, "server.py")
            command += [server_path]
        p = subprocess.Popen(
            command + parameters,
            env=env,
            close_fds=True,
        )
        p.communicate()
        return p.pid

    def communicate(self, data, wait_sleep=0.01):
        encoded_data = pickle.dumps((self._plugin, data))
        self._socket.sendall(encoded_data)
        self._socket.shutdown(socket.SHUT_WR)
        raw_answer = b""
        while True:
            b = self._socket.recv((1024 * 1024))
            if not b:
                break
            raw_answer += b
            time.sleep(wait_sleep)
        try:
            result = json.loads(raw_answer.decode())
            return result
        except json.decoder.JSONDecodeError:
            raise EmbeddedModuleUnexpectedFailure(
                "Cannot decode plugin answer: {0}".format(raw_answer)
            )

    def close(self):
        if self._socket:
            self._socket.close()


@contextmanager
def connect(socket_path, ttl=None, plugin="module"):
    turbo_socket = AnsibleTurboSocket(socket_path=socket_path, ttl=ttl, plugin=plugin)
    try:
        turbo_socket.bind()
        yield turbo_socket
    finally:
        turbo_socket.close()
