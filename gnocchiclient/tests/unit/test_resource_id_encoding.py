#
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

from unittest import mock

import testtools

from gnocchiclient import utils
from gnocchiclient.v1 import metric
from gnocchiclient.v1 import resource

# A Cinder pool name: '@' and '#' are both meaningful in a URL, and an
# unencoded '#' truncates the path so the request hits another resource.
POOL = "ceph-aa@hybrid-rep3#hybrid-rep3"
ENCODED = "ceph-aa%40hybrid-rep3%23hybrid-rep3"


class TestEncodeResourceId(testtools.TestCase):
    def test_encode(self):
        self.assertEqual(ENCODED, utils.encode_resource_id(POOL))
        self.assertEqual("a-uuid-stays-as-is",
                         utils.encode_resource_id("a-uuid-stays-as-is"))
        self.assertEqual("with%2Fslash",
                         utils.encode_resource_id("with/slash"))


class TestResourceUrls(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self.manager = resource.ResourceManager(mock.Mock())

    def test_get(self):
        with mock.patch.object(self.manager, "_get") as m:
            self.manager.get("volume_provider_pool", POOL)
        self.assertEqual("v1/resource/volume_provider_pool/" + ENCODED,
                         m.call_args[0][0])

    def test_get_history(self):
        with mock.patch.object(self.manager, "_get") as m:
            self.manager.get("volume_provider_pool", POOL, history=True)
        self.assertEqual(
            "v1/resource/volume_provider_pool/" + ENCODED + "/history",
            m.call_args[0][0])

    def test_history(self):
        with mock.patch.object(self.manager, "_get") as m:
            self.manager.history("volume_provider_pool", POOL)
        self.assertTrue(m.call_args[0][0].startswith(
            "v1/resource/volume_provider_pool/" + ENCODED + "/history?"))

    def test_update(self):
        with mock.patch.object(self.manager, "_patch") as m:
            self.manager.update("volume_provider_pool", POOL,
                                {"provider": "ceph-aa@hybrid-rep3"})
        self.assertEqual("v1/resource/volume_provider_pool/" + ENCODED,
                         m.call_args[0][0])

    def test_delete(self):
        with mock.patch.object(self.manager, "_delete") as m:
            self.manager.delete(POOL)
        self.assertEqual("v1/resource/generic/" + ENCODED,
                         m.call_args[0][0])


class TestMetricUrls(testtools.TestCase):
    def setUp(self):
        super().setUp()
        self.manager = metric.MetricManager(mock.Mock())

    def test_get_by_name(self):
        with mock.patch.object(self.manager, "_get") as m:
            self.manager.get("volume.provider.pool.capacity.total",
                             resource_id=POOL)
        self.assertEqual(
            "v1/resource/generic/" + ENCODED +
            "/metric/volume.provider.pool.capacity.total",
            m.call_args[0][0])

    def test_create_on_resource(self):
        with mock.patch.object(self.manager, "_post") as m:
            m.return_value.json.return_value = [{}]
            self.manager.create(name="volume.provider.pool.capacity.total",
                                resource_id=POOL)
        self.assertEqual("v1/resource/generic/" + ENCODED + "/metric/",
                         m.call_args[0][0])
