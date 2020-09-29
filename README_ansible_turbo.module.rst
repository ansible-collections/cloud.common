********************
Ansible Turbo Module
********************

.. note:: Better name welcome.

Current situation
=================

The traditional execution flow of an Ansible module includes
the following steps:

- upload of a zip archive with the module and its dependencies
- execution of the module, which is just a Python script
- Ansible collects the results once the script is finished

These steps happen for each task of a playbook, and on every host.

Most of the time, the execution of a module is fast enough for
the user. However sometime, the module requires an important
amount of time, just to initialize itself. This is a common
situation with the API based modules. A classic initialization
involves the following steps:

- load a python library to access the remote resource (SDK)
- open a client
    - load a bunch of Python modules.
    - request a new TCP connection.
    - create a session.
    - and finally, authenticate the client.

All these steps can be time consuming and the same operations
will be run again and again.

For instance, here:

- ``import openstack``: tasks 0.569s
- ``client = openstack.connect()```: 0.065s
- ``client.authorize()```: 1.360s, I run my test against VexxHost public cloud.

In this case, it's a 2s-ish overhead per task. If the playbook
comes with 10 tasks, the execution time cannot go below 20s.

How Ansible Turbo Module improve the situation
==============================================

``AnsibleTurboModule`` is actually a class that inherites from
the standard ``AnsibleModule`` class that your modules probably
already use.
The big difference is that when an module starts, it also spawns
a little Python daemon. If a daemon already exists, it will just
reuse it.
All the module logic is run inside this Python daemon. This means:

- Python modules are actually loaded one time
- Ansible module can reuse an existing authenticated session.

I'm a collection maintainer, How can I enable ```AnsibleTurboModule``?
======================================================================

Your module should inherite from ``AnsibleTurboModule``, instead of ``AnsibleModule``.

.. code-block:: python

  from ansible_module.turbo.module import AnsibleTurboModule as AnsibleModule

You can also use the ``functools.lru_cache()`` decorator to ask Python to cache
the result of an operation, like a network session creation.

Finally, if some of the libraries you depend on are large, it may be nice
to defer your module imports, and do the loading AFTER the
``AnsibleTurboModule`` instance creation.

Example
=======

The Ansible module has to be slightly different. Here an example
with OpenStack and VMware.

This examples use ``functools.lru_cache`` that is the Python core since 3.3.
``lru_cache()`` decorator will managed the cache. It uses the function parameters
as unicity criteria.

- Integration with OpenStack Collection: https://github.com/goneri/ansible-collections-openstack/commit/53ce9860bb84eeab49a46f7a30e3c9588d53e367
- Integration with VMware Collection: https://github.com/goneri/vmware/commit/d1c02b93cbf899fde3a4665e6bcb4d7531f683a3

Demo
====

In this demo, we run one playbook that do several ``os_keypair``
calls. The first time, we run the regular Ansible module.
The second time, we run the same playbook, but with the modified
version.


.. raw:: html

    <a href="https://asciinema.org/a/329481?autoplay=1" target="_blank"><img src="https://asciinema.org/a/329481.png" width="835"/></a>

The daemon
==========

The daemon will kill itself after 15s, and communication are done
through an Unix socket.
It runs in one single process and uses ``asyncio`` internally.
Consequently you can use the ``sync`` keyword in your Ansible module.
This will be handy if you interact with a lot of remote systems
at the same time.
