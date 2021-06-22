==========================
cloud.common Release Notes
==========================

.. contents:: Topics


v2.0.3
======

Bugfixes
--------

- Introduces a fix for the future Python 3.10 (#53)
- turbo - make sure socket doesn't close prematurely, preventing issues with large amounts of data passed as module parameters (https://github.com/ansible-collections/cloud.common/issues/61)

v2.0.2
======

Bugfixes
--------

- Introduces a fix for the future Python 3.10 (#53)
- fail_json method should honor kwargs now when running embedded in server.

v2.0.1
======

Bugfixes
--------

- The profiler is now properly initialized.
- Use the argument_spec values to determine which option should actually be used.
- fix exception messages containing extra single quotes (https://github.com/ansible-collections/cloud.common/pull/46).

v2.0.0
======

Minor Changes
-------------

- The ``EmbeddedModuleFailure`` and ``EmbeddedModuleUnexpectedFailure`` exceptions now handle the ``__repr__`` and ``__str__`` method. This means Python is able to print a meaningful output.
- The modules must now set the ``collection_name`` of the ``AnsibleTurboModule`` class. The content of this attribute is used to build the path of the UNIX socket.
- When the background service is started in a console without the ``--daemon`` flag, it now prints information what it runs.
- ``argument_spec`` is now evaluated server-side.
- fail_json now accept and collect extra named arguments.
- raise an exception if the output of module execution cannot be parsed.
- the ``turbo_demo`` module now return the value of counter.
- the user get an error now an error if a module don't raise ``exit_json()`` or ``fail_json()``.

Bugfixes
--------

- the debug mode now work as expected. The ``_ansible_*`` variables are properly passed to the module.

v1.1.0
======

Minor Changes
-------------

- ansible_module.turbo - the cache is now associated with the collection, if two collections use a cache, two background services will be started.

Bugfixes
--------

- Ensure the background service starts properly on MacOS (https://github.com/ansible-collections/cloud.common/pull/16)
- do not silently skip parameters when the value is ``False``

v1.0.2
======
