#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import shlex
import subprocess
import time
import unittest

import six


class ClientTestBase(unittest.TestCase):
    """Base class for gnocchiclient tests.

    Establishes the gnocchi client and retrieves the essential environment
    information.
    """

    def setUp(self):
        super(ClientTestBase, self).setUp()
        self.cli_dir = os.environ.get('GNOCCHI_CLIENT_EXEC_DIR')
        self.endpoint = os.environ.get('PIFPAF_GNOCCHI_HTTP_URL')

    def openstack(self, action, flags='', params='',
                  fail_ok=False, merge_stderr=False, input=None,
                  has_output=True):
        flags = ((("--os-auth-type gnocchi-basic "
                   "--os-user admin "
                   "--os-endpoint %s") % self.endpoint) + ' ' + flags)
        return self._run("openstack", action, flags, params, fail_ok,
                         merge_stderr, input, has_output)

    def gnocchi(self, action, flags='', params='',
                fail_ok=False, merge_stderr=False, input=None,
                has_output=True):
        flags = ((("--os-auth-plugin gnocchi-basic "
                   "--user admin "
                   "--endpoint %s") % self.endpoint) + ' ' + flags)
        return self._run("gnocchi", action, flags, params, fail_ok,
                         merge_stderr, input, has_output)

    def _run(self, binary, action, flags='', params='',
             fail_ok=False, merge_stderr=False, input=None,
             has_output=True):

        fmt = '-f json' if has_output and action != 'help' else ""

        cmd = ' '.join([os.path.join(self.cli_dir, binary),
                        flags, action, params, fmt])
        if six.PY2:
            cmd = cmd.encode('utf-8')
        cmd = shlex.split(cmd)
        result = ''
        result_err = ''
        stdin = None if input is None else subprocess.PIPE
        stdout = subprocess.PIPE
        stderr = subprocess.STDOUT if merge_stderr else subprocess.PIPE
        proc = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
        result, result_err = proc.communicate(input=input)
        if not fail_ok and proc.returncode != 0:
            raise RuntimeError("Problem running command",
                               proc.returncode,
                               cmd,
                               result,
                               result_err)
        if not six.PY2:
            result = os.fsdecode(result)

        if not has_output and not fail_ok and action != 'help':
            self.assertEqual("", result)

        return result

    def retry_gnocchi(self, retry, *args, **kwargs):
        result = ""
        while not result.strip() and retry > 0:
            result = self.gnocchi(*args, **kwargs)
            if not result:
                time.sleep(1)
                retry -= 1
        return result
