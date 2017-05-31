# -*- encoding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import

import sys

from os_doc_tools import commands

from gnocchiclient import shell

# HACK(jd) Not sure why but Sphinx setup this multiple times, so we just avoid
# doing several times the requests by using this global variable :(
_RUN = False


def get_clients():
    return {'gnocchi': {
        'name': 'A time series storage and resources index service (Gnocchi)',
    }}


def discover_subcommands(os_command, subcommands, extra_params):
    return shell.GnocchiCommandManager.SHELL_COMMANDS.keys()


def setup(app):
    global _RUN
    if _RUN:
        return

    output_dir = "doc/source"
    os_command = 'gnocchi'
    print("Documenting '%s'" % os_command)

    api_name = "Gnocchi API"
    title = "Gnocchi command-line client"

    out_filename = os_command + ".rst"
    out_file = commands.generate_heading(os_command, api_name, title,
                                         output_dir, out_filename,
                                         False)
    if not out_file:
        sys.exit(-1)

    commands.generate_command(os_command, out_file)
    commands.generate_subcommands(
        os_command, out_file,
        list(sorted(shell.GnocchiCommandManager.SHELL_COMMANDS.keys())),
        None, "", "")

    print("Finished.\n")
    out_file.close()

    with open("doc/source/gnocchi.rst", "r") as f:
        data = f.read().splitlines(True)
        for index, line in enumerate(data):
            if "This chapter documents" in line:
                break
    with open("doc/source/gnocchi.rst", "w") as f:
        f.writelines(data[index + 1:])
    _RUN = True
