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
import os
import tempfile
import uuid

from gnocchiclient import auth
from gnocchiclient import client
from gnocchiclient import utils
from gnocchiclient.tests.functional import base


class MetricClientTest(base.ClientTestBase):
    def test_delete_several_metrics(self):
        apname = str(uuid.uuid4())
        # PREPARE AN ARCHIVE POLICY
        self.gnocchi("archive-policy", params="create %s "
                     "--back-window 0 -d granularity:1s,points:86400" % apname)
        # Create 2 metrics
        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name %s" % apname)
        metric1 = json.loads(result)

        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name %s" % apname)
        metric2 = json.loads(result)

        # DELETE
        self.gnocchi('metric', params="delete %s %s"
                     % (metric1["id"], metric2["id"]),
                     has_output=False)

        # GET FAIL
        result = self.gnocchi('metric', params="show %s" % metric1["id"],
                              fail_ok=True, merge_stderr=True)
        self.assertEqual("Metric %s does not exist (HTTP 404)\n" %
                         metric1["id"], result)
        result = self.gnocchi('metric', params="show %s" % metric2["id"],
                              fail_ok=True, merge_stderr=True)
        self.assertEqual("Metric %s does not exist (HTTP 404)\n" %
                         metric2["id"], result)

    def test_metric_listing(self):
        apname = str(uuid.uuid4())
        # PREPARE AN ARCHIVE POLICY
        self.gnocchi("archive-policy", params="create "
                     "-d granularity:1s,points:86400 %s" % apname)
        # Create 1005 metrics
        c = client.Client(
            1,
            session_options={
                'auth': auth.GnocchiBasicPlugin(
                    user="admin", endpoint=self.endpoint)
            },
        )
        for i in range(1005):
            c.metric.create({"archive_policy_name": apname})

        result = self.gnocchi(u'metric', params=u"list")
        self.assertGreaterEqual(len(json.loads(result)), 1005)

        result = self.gnocchi(u'metric', params=u"list"
                              u" --limit 2")
        self.assertEqual(2, len(json.loads(result)))

    def test_metric_measures_exhautic_format(self):
        ap_name = str(uuid.uuid4())
        # PREPARE AN ARCHIVE POLICY
        self.gnocchi("archive-policy", params="create " + ap_name +
                     " --back-window 0 -d granularity:1s,points:86400")
        # CREATE METRIC
        metric_name = str(uuid.uuid4())
        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name " + ap_name + " " + metric_name)
        metric = json.loads(result)

        # MEASURES ADD
        self.gnocchi('measures',
                     params=("add %s "
                             "--measure 'now@42' ")
                     % metric["id"], has_output=False)

        # MEASURES SHOW
        result = self.gnocchi('measures', params="show --refresh " +
                              metric["id"])
        measures = json.loads(result)
        self.assertEqual(1, len(measures))
        self.assertEqual(42, measures[0]['value'])

    def test_metric_measures_show_tz(self):
        ap_name = str(uuid.uuid4())
        # PREPARE AN ARCHIVE POLICY
        self.gnocchi("archive-policy", params="create " + ap_name +
                     " --back-window 0 -d granularity:1s,points:86400")
        # CREATE METRIC
        metric_name = str(uuid.uuid4())
        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name " + ap_name + " " + metric_name)
        metric = json.loads(result)

        # MEASURES ADD
        self.gnocchi('measures',
                     params=("add %s "
                             "-m '2015-03-06T14:33:57Z@43.11' "
                             "--measure '2015-03-06T16:34:12+02:00@12' ")
                     % metric["id"], has_output=False)

        # MEASURES SHOW
        def _delete_tz():
            os.unsetenv("TZ")
        self.addCleanup(_delete_tz)
        os.putenv("TZ", "Europe/Paris")
        result = self.gnocchi('measures', params="show --refresh " +
                              metric["id"])
        measures = json.loads(result)
        self.assertEqual("2015-03-06T15:33:57+01:00", measures[0]['timestamp'])
        self.assertEqual("2015-03-06T15:34:12+01:00", measures[1]['timestamp'])

        # MEASURES SHOW
        result = self.gnocchi('measures', params="show --utc --refresh " +
                              metric["id"])
        measures = json.loads(result)
        # Check that --utc is honored
        self.assertEqual("2015-03-06T14:33:57+00:00", measures[0]['timestamp'])
        self.assertEqual("2015-03-06T14:34:12+00:00", measures[1]['timestamp'])

    def test_metric_scenario(self):
        # PREPARE AN ARCHIVE POLICY
        self.gnocchi("archive-policy", params="create metric-test "
                     "--back-window 0 -d granularity:1s,points:86400")

        # CREATE WITH NAME AND WITHOUT UNIT
        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name metric-test some-name")
        metric = json.loads(result)
        self.assertIsNotNone(metric["id"])
        self.assertEqual("admin", metric["creator"])
        self.assertEqual('some-name', metric["name"])
        self.assertIsNone(metric["unit"])
        self.assertIsNone(metric["resource_id"])
        self.assertIn("metric-test", metric["archive_policy_name"])

        # CREATE WITH UNIT
        result = self.gnocchi(
            u'metric', params=u"create another-name"
            u" --archive-policy-name metric-test"
            u" --unit some-unit")
        metric = json.loads(result)
        self.assertIsNotNone(metric["id"])
        self.assertEqual("admin", metric["creator"])
        self.assertEqual('another-name', metric["name"])
        self.assertEqual('some-unit', metric["unit"])
        self.assertIsNone(metric["resource_id"])
        self.assertIn("metric-test", metric["archive_policy_name"])

        # GET
        result = self.gnocchi('metric', params="show %s" % metric["id"])
        metric_get = json.loads(result)
        # `metric show` format resource/*, `metric create` does not
        metric_get['resource_id'] = metric_get['resource/id']
        del metric_get['resource/id']
        metric_get['archive_policy_name'] = metric_get['archive_policy/name']
        for k in list(metric_get):
            if k.startswith("archive_policy/"):
                del metric_get[k]
        self.assertEqual(metric, metric_get)

        # MEASURES ADD
        self.gnocchi('measures',
                     params=("add %s "
                             "-m '2015-03-06T14:33:57Z@43.11' "
                             "--measure '2015-03-06T14:34:12Z@12' ")
                     % metric["id"], has_output=False)

        # MEASURES GET with refresh
        result = self.gnocchi('measures',
                              params=("show %s "
                                      "--aggregation mean "
                                      "--granularity 1 "
                                      "--start 2015-03-06T14:32:00Z "
                                      "--stop 2015-03-06T14:36:00Z "
                                      "--refresh") % metric["id"])
        measures = json.loads(result)
        self.assertEqual(
            [{'granularity': 1.0,
              'timestamp': utils.dt_to_localtz(
                  utils.parse_date('2015-03-06T14:33:57+00:00')).isoformat(),
              'value': 43.11},
             {'granularity': 1.0,
              'timestamp': utils.dt_to_localtz(
                  utils.parse_date('2015-03-06T14:34:12+00:00')).isoformat(),
              'value': 12.0}], measures)

        # MEASURES GET
        result = self.retry_gnocchi(
            5, 'measures', params=("show %s "
                                   "--aggregation mean "
                                   "--granularity 1 "
                                   "--start 2015-03-06T14:32:00Z "
                                   "--stop 2015-03-06T14:36:00Z"
                                   ) % metric["id"])
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0}
        ], measures)

        # MEASURES GET RESAMPLE
        result = self.retry_gnocchi(
            5, 'measures', params=("show %s "
                                   "--aggregation mean "
                                   "--granularity 1 --resample 3600 "
                                   "--start 2015-03-06T14:32:00Z "
                                   "--stop 2015-03-06T14:36:00Z"
                                   ) % metric["id"])
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 3600.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:00:00+00:00')).isoformat(),
             'value': 27.555}
        ], measures)

        # MEASURES AGGREGATION
        result = self.gnocchi(
            'measures', params=("aggregation "
                                "--metric %s "
                                "--aggregation mean "
                                "--reaggregation sum "
                                "--granularity 1 "
                                "--start 2015-03-06T14:32:00Z "
                                "--stop 2015-03-06T14:36:00Z"
                                ) % metric["id"])
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0}
        ], measures)

        # BATCHING
        measures = json.dumps({
            metric['id']: [{'timestamp': '2015-03-06T14:34:12',
                            'value': 12}]})
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        self.addCleanup(os.remove, tmpfile.name)
        with tmpfile as f:
            f.write(measures.encode('utf8'))
        self.gnocchi('measures', params=("batch-metrics %s" % tmpfile.name),
                     has_output=False)
        self.gnocchi('measures', params="batch-metrics -",
                     input=measures.encode('utf8'),
                     has_output=False)

        # LIST
        result = self.gnocchi('metric', params="list")
        metrics = json.loads(result)
        metric_from_list = [p for p in metrics
                            if p['id'] == metric['id']][0]
        metric['archive_policy/name'] = metric['archive_policy_name']
        for field in ("id", "archive_policy/name", "name",
                      "unit", "resource_id"):
            self.assertEqual(metric[field], metric_from_list[field], field)

        # LIST + limit
        result = self.gnocchi('metric',
                              params=("list "
                                      "--sort name:asc "
                                      "--marker %s "
                                      "--limit 1") % metric['id'])
        metrics = json.loads(result)
        metric_from_list = metrics[0]
        self.assertEqual(1, len(metrics))
        self.assertTrue(metric['name'] < metric_from_list['name'])

        # DELETE
        self.gnocchi('metric', params="delete %s" % metric["id"],
                     has_output=False)

        # GET FAIL
        result = self.gnocchi('metric', params="show %s" % metric["id"],
                              fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Metric %s does not exist (HTTP 404)\n" % metric["id"],
            result)

        # DELETE FAIL
        result = self.gnocchi('metric', params="delete %s" % metric["id"],
                              fail_ok=True, merge_stderr=True,
                              has_output=False)
        self.assertEqual(
            "Metric %s does not exist (HTTP 404)\n" % metric["id"],
            result)

    def test_metric_by_name_scenario(self):
        # PREPARE REQUIREMENT
        self.gnocchi("archive-policy", params="create metric-test2 "
                     "--back-window 0 -d granularity:1s,points:86400")
        self.gnocchi("resource", params="create metric-res")

        metric_name = str(uuid.uuid4())
        # CREATE
        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name metric-test2 -r metric-res %s"
            u" --unit some-unit" % metric_name)
        metric = json.loads(result)
        self.assertIsNotNone(metric["id"])
        self.assertEqual("admin", metric['creator'])
        self.assertEqual(metric_name, metric["name"])
        self.assertEqual('some-unit', metric["unit"])
        self.assertIsNotNone(metric["resource_id"])
        self.assertIn("metric-test", metric["archive_policy/name"])

        # CREATE FAIL
        result = self.gnocchi(
            u'metric', params=u"create"
            u" --archive-policy-name metric-test2 "
            "-r metric-res %s" % metric_name,
            fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Named metric %s already exists (HTTP 409)\n" % metric_name,
            result)

        # GET
        result = self.gnocchi('metric',
                              params="show -r metric-res %s" % metric_name)
        metric_get = json.loads(result)
        # `metric show` returns resource details, `metric create` does not
        metric_get['resource_id'] = metric_get['resource/id']
        for k in list(metric_get):
            if k.startswith("resource/"):
                del metric_get[k]
        self.assertEqual(metric, metric_get)

        # MEASURES ADD
        self.gnocchi('measures',
                     params=("add " + metric_name + " -r metric-res "
                             "-m '2015-03-06T14:33:57Z@43.11' "
                             "--measure '2015-03-06T14:34:12Z@12'"),
                     has_output=False)

        # MEASURES AGGREGATION with refresh
        result = self.gnocchi(
            'measures', params=("aggregation "
                                "--query \"id='metric-res'\" "
                                "--resource-type \"generic\" "
                                "-m " + metric_name + " "
                                "--aggregation mean "
                                "--needed-overlap 0 "
                                "--start 2015-03-06T14:32:00Z "
                                "--stop 2015-03-06T14:36:00Z "
                                "--refresh"))
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0}
        ], measures)

        # MEASURES AGGREGATION
        result = self.gnocchi(
            'measures', params=("aggregation "
                                "--query \"id='metric-res'\" "
                                "--resource-type \"generic\" "
                                "-m  " + metric_name + " "
                                "--aggregation mean "
                                "--needed-overlap 0 "
                                "--start 2015-03-06T14:32:00Z "
                                "--stop 2015-03-06T14:36:00Z"))
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0}
        ], measures)

        # MEASURES AGGREGATION WITH FILL
        result = self.gnocchi(
            'measures', params=("aggregation "
                                "--query \"id='metric-res'\" "
                                "--resource-type \"generic\" "
                                "-m  " + metric_name + " "
                                "--fill 0 "
                                "--granularity 1 "
                                "--start 2015-03-06T14:32:00Z "
                                "--stop 2015-03-06T14:36:00Z"))
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0}
        ], measures)

        # MEASURES AGGREGATION RESAMPLE
        result = self.gnocchi(
            'measures', params=("aggregation "
                                "--query \"id='metric-res'\" "
                                "--resource-type \"generic\" "
                                "-m  " + metric_name + " "
                                "--granularity 1 "
                                "--aggregation mean --resample=3600 "
                                "--needed-overlap 0 "
                                "--start 2015-03-06T14:32:00Z "
                                "--stop 2015-03-06T14:36:00Z"))
        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 3600.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date('2015-03-06T14:00:00+00:00')).isoformat(),
             'value': 27.555}
        ], measures)

        # MEASURES AGGREGATION GROUPBY
        result = self.gnocchi(
            'measures', params=("aggregation "
                                "--groupby project_id "
                                "--groupby user_id "
                                "--query \"id='metric-res'\" "
                                "--resource-type \"generic\" "
                                "-m  " + metric_name + " "
                                "--aggregation mean "
                                "--needed-overlap 0 "
                                "--start 2015-03-06T14:32:00Z "
                                "--stop 2015-03-06T14:36:00Z"))
        measures = json.loads(result)
        self.assertEqual([
            {'group': 'project_id: None, user_id: None',
             'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'group': 'project_id: None, user_id: None',
             'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0},
        ], measures)

        # MEASURES GET
        result = self.gnocchi('measures',
                              params=("show " + metric_name + " -r metric-res "
                                      "--aggregation mean "
                                      "--start 2015-03-06T14:32:00Z "
                                      "--stop 2015-03-06T14:36:00Z"))

        measures = json.loads(result)
        self.assertEqual([
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:33:57+00:00')).isoformat(),
             'value': 43.11},
            {'granularity': 1.0,
             'timestamp': utils.dt_to_localtz(
                 utils.parse_date(u'2015-03-06T14:34:12+00:00')).isoformat(),
             'value': 12.0},
        ], measures)

        # BATCHING
        measures = json.dumps({'metric-res': {metric_name: [{
            'timestamp': '2015-03-06T14:34:12', 'value': 12
        }]}})
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        self.addCleanup(os.remove, tmpfile.name)
        with tmpfile as f:
            f.write(measures.encode('utf8'))

        self.gnocchi('measures', params=("batch-resources-metrics %s" %
                                         tmpfile.name),
                     has_output=False)
        self.gnocchi('measures', params="batch-resources-metrics -",
                     input=measures.encode('utf8'),
                     has_output=False)

        # BATCHING --create-metrics
        measures = json.dumps({'metric-res': {'unknown-metric-name': [{
            'timestamp': '2015-03-06T14:34:12', 'value': 12
        }]}})
        self.gnocchi('measures',
                     params="batch-resources-metrics --create-metrics -",
                     input=measures.encode('utf8'), has_output=False)

        # LIST
        result = self.gnocchi('metric', params="list")
        metrics = json.loads(result)
        metric_from_list = [p for p in metrics
                            if p['archive_policy/name'] == 'metric-test2'][0]
        for field in ["archive_policy/name", "name"]:
            # FIXME(sileht): add "resource_id" or "resource"
            # when LP#1497171 is fixed
            self.assertEqual(metric[field], metric_from_list[field])

        # DELETE
        self.gnocchi('metric',
                     params="delete -r metric-res " + metric_name,
                     has_output=False)

        # GET FAIL
        result = self.gnocchi('metric',
                              params="show -r metric-res " + metric_name,
                              fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Metric " + metric_name + " does not exist (HTTP 404)\n", result)

        # DELETE FAIL
        result = self.gnocchi('metric',
                              params="delete -r metric-res " + metric_name,
                              fail_ok=True, merge_stderr=True,
                              has_output=False)
        self.assertEqual(
            "Metric " + metric_name + " does not exist (HTTP 404)\n",
            result)

        # GET RESOURCE ID
        result = self.gnocchi(
            'resource', params="show -t generic metric-res")
        resource_id = json.loads(result)["id"]

        # DELETE RESOURCE
        self.gnocchi('resource', params="delete metric-res",
                     has_output=False)

        # GET FAIL WITH RESOURCE ERROR
        result = self.gnocchi('metric',
                              params="show " + metric_name + " -r metric-res",
                              fail_ok=True, merge_stderr=True)
        self.assertEqual(
            "Resource %s does not exist (HTTP 404)\n" % resource_id,
            result)
