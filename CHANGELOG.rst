==========================
cloud.common Release Notes
==========================

.. contents:: Topics


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
