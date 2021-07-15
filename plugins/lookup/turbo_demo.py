# Copyright: (c) 2021, Aubin Bikouo (@abikouo)
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
lookup: turbo_demo
author:
  - Aubin Bikouo (@abikouo)

short_description: A demo for cloud.common.plugins.modules_utils.turbo.lookup.
description:
  - return the parent process of the running process
options:
  playbook_vars:
    description: list of playbook variables to add in the output.
    type: list
"""

EXAMPLES = r"""
"""

RETURN = r"""
"""


import os
import sys
import traceback

from ansible_collections.cloud.common.plugins.module_utils.turbo.lookup import (
    TurboLookupBase as LookupBase,
)


def counter():
    counter.i += 1
    return counter.i


# NOTE: workaround to avoid a warning with ansible-doc
if True:  # pylint: disable=using-constant-test
    counter.i = 0


class LookupModule(LookupBase):
    def _run(self, terms, variables=None, playbook_vars=None):
        result = [f"running from pid: {os.getpid()}"]
        if playbook_vars is not None:
            result += [
                variables["vars"].get(x)
                for x in playbook_vars
                if x in variables["vars"]
            ]
        if terms:
            result += terms

        for id, stack in list(sys._current_frames().items()):
            for fname, line_id, name, line in traceback.extract_stack(stack):
                if fname == __file__:
                    continue

        result.append(f"turbo_demo_counter: {counter()}")
        return result

    run = _run if not hasattr(LookupBase, "run_on_daemon") else LookupBase.run_on_daemon
