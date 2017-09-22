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
import json
import uuid

from gnocchiclient.tests.functional import base


class ArchivePolicyClientTest(base.ClientTestBase):
    def test_archive_policy_scenario(self):
        # CREATE
        apname = str(uuid.uuid4())
        result = self.gnocchi(
            u'archive-policy', params=u"create %s"
            u" --back-window 0"
            u" -d granularity:1s,points:86400" % apname)
        policy = json.loads(result)
        self.assertEqual(apname, policy["name"])

        # CREATE FAIL
        result = self.gnocchi(
            u'archive-policy', params=u"create %s"
            u" --back-window 0"
            u" -d granularity:1s,points:86400" % apname,
            fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Archive policy %s already exists (HTTP 409)\n" % apname,
            result)

        # GET
        result = self.gnocchi(
            'archive-policy', params="show %s" % apname)
        policy = json.loads(result)
        self.assertEqual(apname, policy["name"])

        # LIST
        result = self.gnocchi(
            'archive-policy', params="list")
        policies = json.loads(result)
        policy_from_list = [p for p in policies
                            if p['name'] == apname][0]
        for field in ["back_window", "definition", "aggregation_methods"]:
            self.assertEqual(policy[field], policy_from_list[field])

        # UPDATE
        result = self.gnocchi(
            'archive-policy', params='update %s'
            ' -d granularity:1s,points:60' % apname)
        policy = json.loads(result)
        self.assertEqual(apname, policy["name"])

        # UPDATE FAIL
        result = self.gnocchi(
            'archive-policy', params='update %s'
            ' -d granularity:5s,points:86400' % apname,
            fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Archive policy %s does not support change: 1.0 granularity "
            "interval was changed (HTTP 400)\n" % apname,
            result)

        # DELETE
        self.gnocchi('archive-policy',
                     params="delete %s" % apname,
                     has_output=False)

        # GET FAIL
        result = self.gnocchi('archive-policy',
                              params="show %s" % apname,
                              fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Archive policy %s does not exist (HTTP 404)\n" % apname,
            result)

        # DELETE FAIL
        result = self.gnocchi('archive-policy',
                              params="delete %s" % apname,
                              fail_ok=True, merge_stderr=True,
                              has_output=False)
        self.assertEqual(
            "Archive policy %s does not exist (HTTP 404)\n" % apname,
            result)
