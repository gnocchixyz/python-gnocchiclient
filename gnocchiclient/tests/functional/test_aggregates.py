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

from gnocchiclient.tests.functional import base


class AggregatesClientTest(base.ClientTestBase):
    def test_scenario(self):
        # PREPARE AN ARCHIVE POLICY
        self.gnocchi("archive-policy", params="create agg-fetch-test "
                     "--back-window 0 -d granularity:1s,points:86400")

        r1 = json.loads(self.gnocchi("resource", params="create metric-res1"))
        r2 = json.loads(self.gnocchi("resource", params="create metric-res2"))

        # CREATE A METRIC
        result = self.gnocchi(
            u'metric', params=u"create"
            u' -r metric-res1'
            u" --archive-policy-name agg-fetch-test metric-name")
        metric1 = json.loads(result)
        self.assertIsNotNone(metric1["id"])
        self.assertEqual("admin", metric1["creator"])
        self.assertEqual('metric-name', metric1["name"])
        self.assertIsNone(metric1["unit"])
        self.assertIsNotNone(metric1["resource_id"])
        self.assertIn("agg-fetch-test", metric1["archive_policy/name"])

        # CREATE ANOTHER METRIC
        result = self.gnocchi(
            u'metric', params=u"create"
            u' -r metric-res2'
            u" --archive-policy-name agg-fetch-test"
            u" --unit some-unit metric-name")
        metric2 = json.loads(result)
        self.assertIsNotNone(metric2["id"])
        self.assertEqual("admin", metric2["creator"])
        self.assertEqual('metric-name', metric2["name"])
        self.assertEqual('some-unit', metric2["unit"])
        self.assertIsNotNone(metric2["resource_id"])
        self.assertIn("agg-fetch-test", metric2["archive_policy/name"])

        # MEASURES ADD
        self.gnocchi('measures',
                     params=("add %s "
                             "-m '2015-03-06T14:33:57Z@43.11' "
                             "--measure '2015-03-06T14:34:12Z@12' ")
                     % metric1["id"], has_output=False)
        self.gnocchi('measures',
                     params=("add %s "
                             "-m '2015-03-06T14:33:57Z@43.11' "
                             "--measure '2015-03-06T14:34:12Z@12' ")
                     % metric2["id"], has_output=False)

        # MEASURES GET with refresh
        self.gnocchi('measures', params=("show %s "
                                         "--aggregation mean "
                                         "--granularity 1 "
                                         "--refresh") % metric1["id"])
        self.gnocchi('measures', params=("show %s "
                                         "--aggregation mean "
                                         "--granularity 1 "
                                         "--refresh") % metric2["id"])

        # MEASURES AGGREGATION METRIC IDS
        result = self.gnocchi(
            'aggregates', params=("'(+ 2 (metric (%s mean) (%s mean)))' "
                                  "--granularity 1 "
                                  "--start 2015-03-06T14:32:00Z "
                                  "--stop 2015-03-06T14:36:00Z "
                                  ) % (metric1["id"], metric2["id"]))
        measures = json.loads(result)
        self.assertEqual(4, len(measures))
        self.assertIn({'granularity': 1.0,
                       'name': '%s/mean' % metric1["id"],
                       'timestamp': '2015-03-06T14:33:57+00:00',
                       'value': 45.11}, measures)
        self.assertIn({'granularity': 1.0,
                       'name': '%s/mean' % metric1["id"],
                       'timestamp': '2015-03-06T14:34:12+00:00',
                       'value': 14.0}, measures)
        self.assertIn({'granularity': 1.0,
                       'name': '%s/mean' % metric2["id"],
                       'timestamp': '2015-03-06T14:33:57+00:00',
                       'value': 45.11}, measures)
        self.assertIn({'granularity': 1.0,
                       'name': '%s/mean' % metric2["id"],
                       'timestamp': '2015-03-06T14:34:12+00:00',
                       'value': 14.0}, measures)

        # MEASURES AGGREGATION METRIC NAMES
        result = self.gnocchi(
            'aggregates', params=(
                "'(+ 2 (metric metric-name mean))' "
                "'original_resource_id like \"metric-res%\"' "
                "--groupby project_id "
                "--groupby user_id "
                "--resource-type generic "
                "--granularity 1 "
                "--start 2015-03-06T14:32:00Z "
                "--stop 2015-03-06T14:36:00Z "
            ))
        measures = json.loads(result)
        self.assertEqual(4, len(measures))
        self.assertIn({'granularity': 1.0,
                       'group': u'project_id: None, user_id: None',
                       'name': u'%s/metric-name/mean' % r1["id"],
                       'timestamp': u'2015-03-06T14:33:57+00:00',
                       'value': 45.11}, measures)
        self.assertIn({'granularity': 1.0,
                       'group': u'project_id: None, user_id: None',
                       'name': u'%s/metric-name/mean' % r1["id"],
                       'timestamp': u'2015-03-06T14:34:12+00:00',
                       'value': 14.0}, measures)
        self.assertIn({'granularity': 1.0,
                       'group': u'project_id: None, user_id: None',
                       'name': u'%s/metric-name/mean' % r2["id"],
                       'timestamp': u'2015-03-06T14:33:57+00:00',
                       'value': 45.11}, measures)
        self.assertIn({'granularity': 1.0,
                       'group': u'project_id: None, user_id: None',
                       'name': u'%s/metric-name/mean' % r2["id"],
                       'timestamp': u'2015-03-06T14:34:12+00:00',
                       'value': 14.0}, measures)
