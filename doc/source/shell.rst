The :program:`gnocchi` shell utility
=========================================

.. program:: gnocchi
.. highlight:: bash

The :program:`gnocchi` shell utility interacts with Gnocchi from the command
line. It supports the entirety of the Gnocchi API.

Authentication method
+++++++++++++++++++++

You'll need to provide the authentication method and your credentials to
:program:`gnocchi`.

Basic authentication
~~~~~~~~~~~~~~~~~~~~

If you're using Gnocchi with basic authentication, export the following
variables in your environment::

  export OS_AUTH_TYPE=gnocchi-basic
  export GNOCCHI_USER=<youruserid>
  export GNOCCHI_ENDPOINT=http://urlofgnocchi

.. note::

  OS_AUTH_TYPE is used globally by all clients supporting Keystone. Provide
  :option:`--os-auth-plugin` gnocchi-basic to the client instead if other
  clients are used in session.

OpenStack Keystone authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're using Gnocchi with Keystone authentication, export the following
variables in your environment with the appropriate values::

    export OS_AUTH_TYPE=password
    export OS_USERNAME=user
    export OS_PASSWORD=pass
    export OS_TENANT_NAME=myproject
    export OS_AUTH_URL=http://auth.example.com:5000/v2.0

The command line tool will attempt to reauthenticate using your provided
credentials for every request. You can override this behavior by manually
supplying an auth token using :option:`--endpoint` and
:option:`--os-auth-token`. You can alternatively set these environment
variables::

    export GNOCCHI_ENDPOINT=http://gnocchi.example.org:8041
    export OS_AUTH_PLUGIN=token
    export OS_AUTH_TOKEN=3bcc3d3a03f44e3d8377f9247b0ad155

For more details, check the `keystoneauth documentation`_.

.. _`keystoneauth documentation`: https://docs.openstack.org/developer/keystoneauth/


Timestamps
++++++++++

By default, timestamps are displayed in local time zone. If you prefer to see
timestamps dispalyed in UTC time zones, you can pass the `--utc` option to the
command.

The `gnocchi` command line interface parses timestamps in the `ISO8601`_
format. If no time zone is specified, timestamps are assumed to be in the local
client time zone.

.. _`ISO8601`: https://en.wikipedia.org/wiki/ISO_8601

Commands descriptions
+++++++++++++++++++++

.. autodoc-gnocchi:: gnocchiclient.shell.GnocchiShell
   :application: gnocchi

.. autodoc-gnocchi:: openstack.metric.v1
   :application: gnocchi
