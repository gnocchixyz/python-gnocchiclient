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

import datetime
import uuid

from debtcollector import removals

import iso8601

import ujson

from gnocchiclient import utils
from gnocchiclient.v1 import base


class MetricManager(base.Manager):
    metric_url = "v1/metric/"
    resource_url = "v1/resource/generic/%s/metric/"
    metric_batch_url = "v1/batch/metrics/measures"
    resources_batch_url = "v1/batch/resources/metrics/measures"

    def list(self, limit=None, marker=None, sorts=None):
        """List metrics.

        :param limit: maximum number of resources to return
        :type limit: int
        :param marker: the last item of the previous page; we return the next
                       results after this value.
        :type marker: str
        :param sorts: list of resource attributes to order by. (example
                      ["user_id:desc-nullslast", "project_id:asc"]
        :type sorts: list of str
        """
        params = utils.build_pagination_options(False, False, limit, marker,
                                                sorts)
        metrics = []
        page_url = "%s?%s" % (self.metric_url[:-1],
                              utils.dict_to_querystring(params))
        while page_url:
            page = self._get(page_url)
            metrics.extend(page.json())
            if limit is None or len(metrics) < limit:
                page_url = page.links.get("next", {'url': None})['url']
            else:
                break
        return metrics

    @staticmethod
    def _ensure_metric_is_uuid(metric, attribute="resource_id"):
        try:
            uuid.UUID(metric)
        except ValueError:
            raise TypeError("%s is required to get a metric by name" %
                            attribute)

    def get(self, metric, resource_id=None):
        """Get an metric.

        :param metric: ID or Name of the metric
        :type metric: str
        :param resource_id: ID of the resource (required
                            to get a metric by name)
        :type resource_id: str
        """
        if resource_id is None:
            self._ensure_metric_is_uuid(metric)
            url = self.metric_url + metric
        else:
            url = (self.resource_url % resource_id) + metric
        return self._get(url).json()

    # FIXME(jd): This is what create will be after debtcollector warnings have
    # been removed. We provide it right now for the benchmark code, that can't
    # pickle a debtcollector-ed method.
    def _create_new(self, name=None, archive_policy_name=None,
                    resource_id=None, unit=None):
        """Create an metric.

        :param name: Metric name.
        :type name: str
        :param archive_policy_name: Archive policy name.
        :type archive_policy_name: str
        :param resource_id: The resource ID to attach the metric to.
        :type resource_id: str
        :param unit: The unit of the metric.
        :type unit: str
        """
        metric = {}
        if name is not None:
            metric["name"] = name
        if archive_policy_name is not None:
            metric["archive_policy_name"] = archive_policy_name
        if unit is not None:
            metric["unit"] = unit

        if resource_id is None:
            return self._post(
                self.metric_url, headers={'Content-Type': "application/json"},
                data=ujson.dumps(metric)).json()

        if name is None:
            raise TypeError(
                "Metric name is required if resource_id is set")

        return self._post(
            self.resource_url % resource_id,
            headers={'Content-Type': "application/json"},
            data=ujson.dumps({name: metric})).json()[0]

    # FIXME(jd): remove refetch_metric when LP#1497171 is fixed
    @removals.removed_kwarg("refetch_metric")
    @removals.removed_kwarg("metric")
    def create(self, metric=None, refetch_metric=True,
               name=None,
               archive_policy_name=None,
               resource_id=None,
               unit=None):
        """Create an metric.

        :param name: Metric name.
        :type name: str
        :param archive_policy_name: Archive policy name.
        :type archive_policy_name: str
        :param resource_id: The resource ID to attach the metric to.
        :type resource_id: str
        :param unit: The unit of the metric.
        :type unit: str
        """
        if metric is None:
            metric = {}
            if name is not None:
                metric["name"] = name
            if archive_policy_name is not None:
                metric["archive_policy_name"] = archive_policy_name
            if resource_id is not None:
                metric["resource_id"] = resource_id
            if unit is not None:
                metric["unit"] = unit

        resource_id = metric.get('resource_id')

        if resource_id is None:
            metric = self._post(
                self.metric_url, headers={'Content-Type': "application/json"},
                data=ujson.dumps(metric)).json()
            # FIXME(sileht): create and get have a
            # different output: LP#1497171
            if refetch_metric:
                return self.get(metric["id"])
            return metric

        metric_name = metric.get('name')

        if metric_name is None:
            raise TypeError("metric_name is required if resource_id is set")

        del metric['resource_id']
        metric = {metric_name: metric}
        metric = self._post(
            self.resource_url % resource_id,
            headers={'Content-Type': "application/json"},
            data=ujson.dumps(metric))
        return self.get(metric_name, resource_id)

    def delete(self, metric, resource_id=None):
        """Delete an metric.

        :param metric: ID or Name of the metric
        :type metric: str
        :param resource_id: ID of the resource (required
                            to get a metric by name)
        :type resource_id: str
        """
        if resource_id is None:
            self._ensure_metric_is_uuid(metric)
            url = self.metric_url + metric
        else:
            url = self.resource_url % resource_id + metric
        self._delete(url)

    def add_measures(self, metric, measures, resource_id=None):
        """Add measurements to a metric.

        :param metric: ID or Name of the metric
        :type metric: str
        :param resource_id: ID of the resource (required
                            to get a metric by name)
        :type resource_id: str
        :param measures: measurements
        :type measures: list of dict(timestamp=timestamp, value=float)
        """
        if resource_id is None:
            self._ensure_metric_is_uuid(metric)
            url = self.metric_url + metric + "/measures"
        else:
            url = self.resource_url % resource_id + metric + "/measures"
        return self._post(
            url, headers={'Content-Type': "application/json"},
            data=ujson.dumps(measures))

    def batch_metrics_measures(self, measures):
        """Add measurements to metrics.

        :param measures: measurements
        :type dict(metric_id: list of dict(timestamp=timestamp, value=float))
        """
        return self._post(
            self.metric_batch_url,
            headers={'Content-Type': "application/json"},
            data=ujson.dumps(measures))

    def batch_resources_metrics_measures(self, measures, create_metrics=False):
        """Add measurements to named metrics if resources.

        :param measures: measurements
        :type dict(resource_id: dict(metric_name:
            list of dict(timestamp=timestamp, value=float)))
        """
        return self._post(
            self.resources_batch_url,
            headers={'Content-Type': "application/json"},
            data=ujson.dumps(measures),
            params=dict(create_metrics=create_metrics))

    def get_measures(self, metric, start=None, stop=None, aggregation=None,
                     granularity=None, resource_id=None, refresh=False,
                     resample=None, **kwargs):
        """Get measurements of a metric.

        :param metric: ID or Name of the metric
        :type metric: str
        :param start: beginning of the period
        :type start: timestamp
        :param stop: end of the period
        :type stop: timestamp
        :param aggregation: aggregation to retrieve
        :type aggregation: str
        :param granularity: granularity to retrieve (in seconds)
        :type granularity: int
        :param resource_id: ID of the resource (required
                            to get a metric by name)
        :type resource_id: str
        :param refresh: force aggregation of all known measures
        :type refresh: bool
        :param resample: resample measures to new granularity
        :type resample: float

        All other arguments are arguments are dedicated to custom aggregation
        method passed as-is to the Gnocchi.
        """
        if isinstance(start, datetime.datetime):
            start = start.isoformat()
        if isinstance(stop, datetime.datetime):
            stop = stop.isoformat()

        params = dict(start=start, stop=stop, aggregation=aggregation,
                      granularity=granularity, refresh=refresh,
                      resample=resample)
        params.update(kwargs)
        if resource_id is None:
            self._ensure_metric_is_uuid(metric)
            url = self.metric_url + metric + "/measures"
        else:
            url = self.resource_url % resource_id + metric + "/measures"
        measures = self._get(url, params=params).json()
        return [(iso8601.parse_date(ts), g, value)
                for ts, g, value in measures]

    def aggregation(self, metrics, query=None,
                    start=None, stop=None, aggregation=None,
                    reaggregation=None, granularity=None,
                    needed_overlap=None, resource_type="generic",
                    groupby=None, refresh=False, resample=None, fill=None):
        """Get measurements of an aggregated metrics.

        :param metrics: IDs of metric or metric name
        :type metric: list or str
        :param query: The query dictionary
        :type query: dict
        :param start: beginning of the period
        :type start: timestamp
        :param stop: end of the period
        :type stop: timestamp
        :param aggregation: granularity aggregation function to retrieve
        :type aggregation: str
        :param reaggregation: groupby aggregation function to retrieve
        :type reaggregation: str
        :param granularity: granularity to retrieve (in seconds)
        :type granularity: int
        :param needed_overlap: percent of datapoints in each metrics required
        :type needed_overlap: float
        :param resource_type: type of resource for the query
        :type resource_type: str
        :param groupby: list of attribute to group by
        :type groupby: list
        :param refresh: force aggregation of all known measures
        :type refresh: bool
        :param resample: resample measures to new granularity
        :type resample: float
        :param fill: value to use when backfilling missing datapoints
        :type fill: float or 'null'

        See Gnocchi REST API documentation for the format
        of *query dictionary*
        http://docs.openstack.org/developer/gnocchi/rest.html#searching-for-resources
        """
        if isinstance(start, datetime.datetime):
            start = start.isoformat()
        if isinstance(stop, datetime.datetime):
            stop = stop.isoformat()

        params = dict(start=start, stop=stop, aggregation=aggregation,
                      reaggregation=reaggregation, granularity=granularity,
                      needed_overlap=needed_overlap, groupby=groupby,
                      refresh=refresh, resample=resample, fill=fill)
        if query is None:
            for metric in metrics:
                self._ensure_metric_is_uuid(metric)
            params['metric'] = metrics
            measures = self._get("v1/aggregation/metric",
                                 params=params).json()
        else:
            if isinstance(query, dict):
                measures = self._post(
                    "v1/aggregation/resource/%s/metric/%s?%s" % (
                        resource_type, metrics,
                        utils.dict_to_querystring(params)),
                    headers={'Content-Type': "application/json"},
                    data=ujson.dumps(query)).json()
            else:
                params['filter'] = query
                measures = self._post(
                    "v1/aggregation/resource/%s/metric/%s?%s" % (
                        resource_type, metrics,
                        utils.dict_to_querystring(params)),
                    headers={'Content-Type': "application/json"}).json()
        if groupby is None:
            return [(iso8601.parse_date(ts), g, value)
                    for ts, g, value in measures]

        for group in measures:
            group["measures"] = [
                (iso8601.parse_date(ts), g, value)
                for ts, g, value in group["measures"]
            ]

        return measures
