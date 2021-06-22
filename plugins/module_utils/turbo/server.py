import argparse
import asyncio
import importlib

# py38 only, See: https://github.com/PyCQA/pylint/issues/2976
import inspect  # pylint: disable=syntax-error
import io
import json

# py38 only, See: https://github.com/PyCQA/pylint/issues/2976
import collections  # pylint: disable=syntax-error
import os
import signal
import sys
import traceback
import zipfile
from zipimport import zipimporter


from .exceptions import (
    EmbeddedModuleFailure,
    EmbeddedModuleUnexpectedFailure,
    EmbeddedModuleSuccess,
)

sys_path_lock = None

import ansible.module_utils.basic

please_include_me = "bar"


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


class EmbeddedModule:
    def __init__(self, ansiblez_path, params):
        self.ansiblez_path = ansiblez_path
        self.collection_name, self.module_name = self.find_module_name()
        self.params = params
        self.module_class = None
        self.debug_mode = False
        self.module_path = (
            "ansible_collections.{collection_name}." "plugins.modules.{module_name}"
        ).format(collection_name=self.collection_name, module_name=self.module_name)

    def find_module_name(self):
        with zipfile.ZipFile(self.ansiblez_path) as zip:
            for path in zip.namelist():
                if not path.startswith("ansible_collections"):
                    continue
                if not path.endswith(".py"):
                    continue
                if path.endswith("__init__.py"):
                    continue
                splitted = path.split("/")
                if len(splitted) != 6:
                    continue
                if splitted[-3:-1] != ["plugins", "modules"]:
                    continue
                collection = ".".join(splitted[1:3])
                name = splitted[-1][:-3]
                return collection, name
        raise Exception("Cannot find module name")

    async def load(self):
        async with sys_path_lock:
            # Add the Ansiblez_path in sys.path
            sys.path.insert(0, self.ansiblez_path)

            # resettle the loaded modules that were associated
            # with a different Ansiblez.
            for path, module in tuple(sys.modules.items()):
                if path and module and path.startswith("ansible_collections"):
                    try:
                        prefix = sys.modules[path].__loader__.prefix
                    except AttributeError:
                        # Not from a zipimporter loader, skipping
                        continue
                    py_path = self.ansiblez_path + os.sep + prefix
                    my_loader = zipimporter(py_path)
                    sys.meta_path.append(my_loader)
                    if hasattr(sys.modules[path], "__path__"):
                        sys.modules[path].__path__ = py_path

            # Finally, load the plugin class.
            self.module_class = importlib.import_module(self.module_path)

    async def unload(self):
        async with sys_path_lock:
            sys.path = [i for i in sys.path if i != self.ansiblez_path]
            sys.meta_path = [
                i
                for i in sys.meta_path
                if not (isinstance(i, zipimporter) and i.archive == self.ansiblez_path)
            ]

    def create_profiler(self):
        if self.debug_mode:
            import cProfile

            pr = cProfile.Profile()
            pr.enable()
            return pr

    def print_profiling_info(self, pr):
        if self.debug_mode:
            import pstats

            sortby = pstats.SortKey.CUMULATIVE
            ps = pstats.Stats(pr).sort_stats(sortby)
            ps.print_stats(20)

    def print_backtrace(self, backtrace):
        if self.debug_mode:
            print(backtrace)  # pylint: disable=ansible-bad-function

    async def run(self):
        class FakeStdin:
            buffer = None

        # monkeypatching to pass the argument to the module, this is not
        # really safe, and in the future, this will prevent us to run several
        # modules in parallel. We can maybe use a scoped monkeypatch instead
        _fake_stdin = FakeStdin()
        _fake_stdin.buffer = io.BytesIO(self.params.encode())
        sys.stdin = _fake_stdin
        # Trick to be sure ansible.module_utils.basic._load_params() won't
        # try to build the module parameters from the daemon arguments
        sys.argv = sys.argv[:1]
        ansible.module_utils.basic._ANSIBLE_ARGS = None
        pr = self.create_profiler()
        if not hasattr(self.module_class, "main"):
            raise EmbeddedModuleFailure("No main() found!")
        try:
            if inspect.iscoroutinefunction(self.module_class.main):
                await self.module_class.main()
            elif pr:
                pr.runcall(self.module_class.main)
            else:
                self.module_class.main()
        except EmbeddedModuleSuccess as e:
            self.print_profiling_info(pr)
            return e.kwargs
        except EmbeddedModuleFailure as e:
            backtrace = traceback.format_exc()
            self.print_backtrace(backtrace)
            raise
        except Exception as e:
            backtrace = traceback.format_exc()
            self.print_backtrace(backtrace)
            raise EmbeddedModuleUnexpectedFailure(str(backtrace))
        else:
            raise EmbeddedModuleUnexpectedFailure(
                "Likely a bug: exit_json() or fail_json() should be called during the module excution"
            )


class AnsibleVMwareTurboMode:
    def __init__(self):
        self.sessions = collections.defaultdict(dict)
        self.socket_path = None
        self.ttl = None
        self.debug_mode = None

    async def ghost_killer(self):
        await asyncio.sleep(self.ttl)
        self.stop()

    async def handle(self, reader, writer):
        self._watcher.cancel()

        raw_data = await reader.read()
        if not raw_data:
            return

        (
            ansiblez_path,
            params,
        ) = json.loads(raw_data)
        if self.debug_mode:
            print(  # pylint: disable=ansible-bad-function
                f"-----\nrunning {ansiblez_path} with params: ¨{params}¨"
            )

        embedded_module = EmbeddedModule(ansiblez_path, params)
        if self.debug_mode:
            embedded_module.debug_mode = True

        await embedded_module.load()
        try:
            result = await embedded_module.run()
        except SystemExit:
            backtrace = traceback.format_exc()
            result = {"msg": str(backtrace), "failed": True}
        except EmbeddedModuleFailure as e:
            result = {"msg": str(e), "failed": True}
            if e.kwargs:
                result.update(e.kwargs)
        except Exception as e:
            result = {"msg": traceback.format_stack() + [str(e)], "failed": True}

        writer.write(json.dumps(result).encode())
        writer.close()
        self._watcher = self.loop.create_task(self.ghost_killer())

        await embedded_module.unload()

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
    sys_path_lock = asyncio.Lock()

    server = AnsibleVMwareTurboMode()
    server.socket_path = args.socket_path
    server.ttl = args.ttl
    server.debug_mode = not args.fork
    server.start()
