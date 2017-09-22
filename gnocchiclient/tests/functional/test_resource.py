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


class ResourceClientTest(base.ClientTestBase):
    RESOURCE_ID = str(uuid.uuid4())
    RESOURCE_ID2 = "foo"
    PROJECT_ID = str(uuid.uuid4())

    def test_help(self):
        self.gnocchi("help", params="resource list")
        self.gnocchi("help", params="resource history")
        self.gnocchi("help", params="resource search")

    def test_resource_scenario(self):
        apname = str(uuid.uuid4())
        # Create an archive policy
        self.gnocchi(
            u'archive-policy', params=u"create %s"
            u" -d granularity:1s,points:86400" % apname)

        # CREATE
        result = self.gnocchi(
            u'resource', params=u"create %s --type generic" %
            self.RESOURCE_ID)
        resource = json.loads(result)
        self.assertEqual(self.RESOURCE_ID, resource["id"])
        self.assertIsNone(resource["project_id"])
        self.assertIsNotNone(resource["started_at"])

        # CREATE FAIL
        result = self.gnocchi('resource',
                              params="create generic -a id:%s" %
                              self.RESOURCE_ID,
                              fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Resource %s already exists (HTTP 409)\n" % self.RESOURCE_ID,
            result)

        # UPDATE
        result = self.gnocchi(
            'resource', params=("update -t generic %s -a project_id:%s "
                                "-n temperature:%s" %
                                (self.RESOURCE_ID, self.PROJECT_ID, apname)))
        resource_updated = json.loads(result)
        self.assertEqual(self.RESOURCE_ID, resource_updated["id"])
        self.assertEqual(self.PROJECT_ID, resource_updated["project_id"])
        self.assertEqual(resource["started_at"],
                         resource_updated["started_at"])
        self.assertIn("temperature", resource_updated["metrics"])

        # GET
        result = self.gnocchi(
            'resource', params="show -t generic %s" % self.RESOURCE_ID)
        resource_got = json.loads(result)
        self.assertEqual(self.RESOURCE_ID, resource_got["id"])
        self.assertEqual(self.PROJECT_ID, resource_got["project_id"])
        self.assertEqual(resource["started_at"], resource_got["started_at"])
        self.assertIn("temperature", resource_got["metrics"])

        # HISTORY
        result = self.gnocchi(
            'resource', params="history --type generic %s" % self.RESOURCE_ID)
        resource_history = json.loads(result)
        self.assertEqual(2, len(resource_history))
        self.assertEqual(self.RESOURCE_ID, resource_history[0]["id"])
        self.assertEqual(self.RESOURCE_ID, resource_history[1]["id"])
        self.assertIsNone(resource_history[0]["project_id"])
        self.assertEqual(self.PROJECT_ID, resource_history[1]["project_id"])

        # LIST
        result = self.gnocchi('resource', params="list -t generic")
        self.assertIn(self.RESOURCE_ID,
                      [r['id'] for r in json.loads(result)])
        resource_list = [r for r in json.loads(result)
                         if r['id'] == self.RESOURCE_ID][0]
        self.assertEqual(self.RESOURCE_ID, resource_list["id"])
        self.assertEqual(self.PROJECT_ID, resource_list["project_id"])
        self.assertEqual(resource["started_at"], resource_list["started_at"])

        # Search
        result = self.gnocchi('resource',
                              params=("search --type generic "
                                      "'project_id=%s'"
                                      ) % self.PROJECT_ID)
        resource_list = json.loads(result)[0]
        self.assertEqual(self.RESOURCE_ID, resource_list["id"])
        self.assertEqual(self.PROJECT_ID, resource_list["project_id"])
        self.assertEqual(resource["started_at"], resource_list["started_at"])

        # UPDATE with Delete metric
        result = self.gnocchi(
            'resource', params=("update -t generic %s -a project_id:%s "
                                "-d temperature" %
                                (self.RESOURCE_ID, self.PROJECT_ID)))
        resource_updated = json.loads(result)
        self.assertNotIn("temperature", resource_updated["metrics"])

        result = self.gnocchi(
            'resource', params=("update %s -d temperature" % self.RESOURCE_ID),
            fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Metric name temperature not found\n",
            result)

        # CREATE 2
        result = self.gnocchi(
            'resource', params=("create %s -t generic "
                                "-a project_id:%s"
                                ) % (self.RESOURCE_ID2, self.PROJECT_ID))
        resource2 = json.loads(result)
        self.assertEqual(self.RESOURCE_ID2,
                         resource2["original_resource_id"])
        self.assertEqual(self.PROJECT_ID, resource2["project_id"])
        self.assertIsNotNone(resource2["started_at"])

        # Search + limit + short
        result = self.gnocchi('resource',
                              params=("search "
                                      "-t generic "
                                      "'project_id=%s' "
                                      "--sort started_at:asc "
                                      "--marker %s "
                                      "--limit 1"
                                      ) % (self.PROJECT_ID, self.RESOURCE_ID))
        resource_limit = json.loads(result)[0]
        self.assertEqual(self.RESOURCE_ID2,
                         resource_limit["original_resource_id"])
        self.assertEqual(self.PROJECT_ID, resource_limit["project_id"])
        self.assertEqual(resource2["started_at"], resource_limit["started_at"])

        # DELETE
        self.gnocchi('resource',
                     params="delete %s" % self.RESOURCE_ID,
                     has_output=False)
        self.gnocchi('resource',
                     params="delete %s" % self.RESOURCE_ID2,
                     has_output=False)

        # GET FAIL
        result = self.gnocchi('resource',
                              params="show --type generic %s" %
                              self.RESOURCE_ID,
                              fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Resource %s does not exist (HTTP 404)\n" % self.RESOURCE_ID,
            result)

        # DELETE FAIL
        result = self.gnocchi('resource',
                              params="delete %s" % self.RESOURCE_ID,
                              fail_ok=True, merge_stderr=True,
                              has_output=False)
        self.assertEqual(
            "Resource %s does not exist (HTTP 404)\n" % self.RESOURCE_ID,
            result)

        # Create and Batch Delete
        result1 = self.gnocchi(
            u'resource', params=u"create %s --type generic" %
            self.RESOURCE_ID)
        result2 = self.gnocchi(
            u'resource', params=u"create %s --type generic" %
            self.RESOURCE_ID2)
        resource1 = json.loads(result1)
        resource2 = json.loads(result2)
        self.assertEqual(self.RESOURCE_ID, resource1['id'])
        self.assertEqual(self.RESOURCE_ID2, resource2['original_resource_id'])
        result3 = self.gnocchi(
            'resource batch delete ',
            params=("'id in [%s, %s]' "
                    "-t generic") % (resource1["id"], resource2["id"]))
        resource3 = json.loads(result3)
        self.assertEqual(2, int(resource3["deleted"]))
        result4 = self.gnocchi(
            'resource batch delete ',
            params=("'id in [%s, %s]' "
                    "-t generic") % (resource1["id"], resource2["id"]))
        resource4 = json.loads(result4)
        self.assertEqual(0, int(resource4["deleted"]))

        # LIST EMPTY
        result = self.gnocchi('resource', params="list -t generic")
        resource_ids = [r['id'] for r in json.loads(result)]
        self.assertNotIn(self.RESOURCE_ID, resource_ids)
        self.assertNotIn(self.RESOURCE_ID2, resource_ids)
