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

import fnmatch

from cliff import sphinxext

from gnocchiclient import shell


class GnocchiAutoDocDirective(sphinxext.AutoprogramCliffDirective):
    def _load_commands(self):
        command_pattern = self.options.get('command')
        full_cmd_list = shell.GnocchiCommandManager.SHELL_COMMANDS.keys()
        if command_pattern:
            commands = [x for x in full_cmd_list
                        if fnmatch.fnmatch(x, command_pattern)]
        else:
            commands = full_cmd_list
        return dict((name, shell.GnocchiCommandManager.SHELL_COMMANDS[name])
                    for name in commands)


def setup(app):
    app.add_directive('autodoc-gnocchi', GnocchiAutoDocDirective)
    app.add_config_value('autoprogram_cliff_application', 'gnocchi', True)
    app.add_config_value('autoprogram_cliff_ignored', ['--help'], True)
