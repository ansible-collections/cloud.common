import argparse
import asyncio
import json
from math import pi

# py38 only, See: https://github.com/PyCQA/pylint/issues/2976
import os
import signal
import sys
import traceback
import pickle

# from ansible.utils.collection_loader import AnsibleCollectionLoader
import ansible.plugins.loader as plugin_loader
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar
from ansible.module_utils._text import to_native


def fork_process():
    """
    This function performs the double fork process to detach from the
    parent process and execute.
    """
    pid = os.fork()

    if pid == 0:
        fd = os.open(os.devnull, os.O_RDWR)

        # clone stdin/out/err
        for num in range(3):
            if fd != num:
                os.dup2(fd, num)

        if fd not in range(3):
            os.close(fd)

        pid = os.fork()
        if pid > 0:
            os._exit(0)

        # get new process session and detach
        sid = os.setsid()
        if sid == -1:
            raise Exception("Unable to detach session while daemonizing")

        # avoid possible problems with cwd being removed
        os.chdir("/")

        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # pylint: disable=ansible-bad-function
    else:
        sys.exit(0)  # pylint: disable=ansible-bad-function
    return pid


def load_lookup_plugin(name, variables=None):
    templar = Templar(loader=DataLoader(), variables=variables)
    ansible_collections = "ansible_collections."
    if name.startswith(ansible_collections):
        name = name.replace(ansible_collections, "", 1)
    ansible_plugins_lookup = ".plugins.lookup."
    if ansible_plugins_lookup in name:
        name = name.replace(ansible_plugins_lookup, ".", 1)
    return plugin_loader.lookup_loader.get(
        name=name, loader=templar._loader, templar=templar
    )


class Server:
    def __init__(self, path, ttl):
        self.socket_path = path
        self.ttl = ttl

    async def ghost_killer(self):
        await asyncio.sleep(self.ttl)
        self.stop()

    async def handle(self, reader, writer):
        self._watcher.cancel()
        errors = None
        try:
            raw_data = await reader.read()
            if not raw_data:
                return

            (
                lookup_name,
                terms,
                variables,
                kwargs,
            ) = pickle.loads(raw_data)

            instance = load_lookup_plugin(lookup_name)

            instance = load_lookup_plugin(lookup_name)
            result = instance._run(terms, variables=variables, **kwargs)

        except Exception as e:
            errors = to_native(e)

        writer.write(json.dumps([result, errors]).encode())
        writer.close()
        self._watcher = self.loop.create_task(self.ghost_killer())

    def start(self):
        self.loop = asyncio.get_event_loop()
        self.loop.add_signal_handler(signal.SIGTERM, self.stop)
        self._watcher = self.loop.create_task(self.ghost_killer())

        import sys

        if sys.hexversion >= 0x30A00B1:
            # py3.10 drops the loop argument of create_task.
            self.loop.create_task(
                asyncio.start_unix_server(self.handle, path=self.socket_path)
            )
        else:
            self.loop.create_task(
                asyncio.start_unix_server(
                    self.handle, path=self.socket_path, loop=self.loop
                )
            )
        self.loop.run_forever()

    def stop(self):
        os.unlink(self.socket_path)
        self.loop.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start a background daemon.")
    parser.add_argument("--socket-path")
    parser.add_argument("--ttl", default=15, type=int)
    parser.add_argument("--fork", action="store_true")

    args = parser.parse_args()
    if args.fork:
        fork_process()
    server = Server(args.socket_path, args.ttl)
    server.start()
