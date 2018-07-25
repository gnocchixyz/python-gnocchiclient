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

import iso8601

import ujson

from gnocchiclient import utils
from gnocchiclient.v1 import base


class AggregatesManager(base.Manager):
    def fetch(self, operations, search=None,
              resource_type='generic', start=None, stop=None, granularity=None,
              needed_overlap=None, groupby=None, fill=None, details=False):
        """Get measurements of an aggregated metrics.

        :param operations: operations
        :type operations: list or str
        :param start: beginning of the period
        :type start: timestamp
        :param stop: end of the period
        :type stop: timestamp
        :param granularity: granularity to retrieve (in seconds)
        :type granularity: int
        :param needed_overlap: percent of datapoints in each metrics required
        :type needed_overlap: float
        :param groupby: list of attribute to group by
        :type groupby: list
        :param fill: value to use when backfilling missing datapoints
        :type fill: float or 'null'
        :param details: also returns the list of metrics or resources
                        associated to the operations
        :type details: boolean

        See Gnocchi REST API documentation for the format
        of *query dictionary*
        http://docs.openstack.org/developer/gnocchi/rest.html#aggregates
        """
        if isinstance(start, datetime.datetime):
            start = start.isoformat()
        if isinstance(stop, datetime.datetime):
            stop = stop.isoformat()

        params = dict(start=start, stop=stop,
                      granularity=granularity,
                      needed_overlap=needed_overlap,
                      fill=fill,
                      details=details)

        data = dict(operations=operations)
        if search is not None:
            data["search"] = search
            data["resource_type"] = resource_type
            params["groupby"] = groupby

        aggregates = self._post("v1/aggregates?%s" % (
            utils.dict_to_querystring(params)),
            headers={'Content-Type': "application/json"},
            data=ujson.dumps(data)).json()

        if search is not None and groupby is not None:
            for group in aggregates:
                self._convert_dates(group["measures"]["measures"])
        else:
            self._convert_dates(aggregates["measures"])
        return aggregates

    @classmethod
    def _convert_dates(cls, data):
        # NOTE(sileht): browse to aggregates measures dict tree and convert
        # date when we found timeseries, dict can looks like
        # {"aggregated": ...}, {"metric_id": {"agg": ...}} or
        # {"resource_id": {"metric_name": {"agg": ...}}}
        for key in data:
            if isinstance(data[key], list):
                data[key] = [(iso8601.parse_date(ts), g, value)
                             for ts, g, value in data[key]]
            elif isinstance(data[key], dict):
                cls._convert_dates(data[key])
            else:
                raise RuntimeError("Unexpected aggregates API output %s" %
                                   data[key])
