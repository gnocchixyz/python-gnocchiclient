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
from gnocchiclient import utils


class CliAggregates(utils.Lister):
    """Get measurements of aggregated metrics"""

    COLS = ('name', 'timestamp', 'granularity', 'value')

    def get_parser(self, prog_name):
        parser = super(CliAggregates, self).get_parser(prog_name)
        parser.add_argument("operations",
                            help="Operations to apply to time series")
        utils.add_query_argument("search", parser, nargs="?", default=None)
        parser.add_argument("--resource-type", default="generic",
                            help="Resource type to query"),
        parser.add_argument("--start",
                            help="beginning of the period")
        parser.add_argument("--stop",
                            help="end of the period")
        parser.add_argument("--granularity",
                            help="granularity to retrieve")
        parser.add_argument("--needed-overlap", type=float,
                            help=("percentage of overlap across datapoints"))
        parser.add_argument("--groupby",
                            action='append',
                            help="Attribute to use to group resources"),
        parser.add_argument("--fill",
                            help=("Value to use when backfilling timestamps "
                                  "with missing values in a subset of series. "
                                  "Value should be a float or 'null'."))
        return parser

    def take_action(self, parsed_args):
        aggregates = utils.get_client(self).aggregates.fetch(
            operations=parsed_args.operations,
            resource_type=parsed_args.resource_type,
            search=parsed_args.search,
            start=parsed_args.start,
            stop=parsed_args.stop,
            granularity=parsed_args.granularity,
            needed_overlap=parsed_args.needed_overlap,
            groupby=parsed_args.groupby,
        )
        if parsed_args.groupby:
            ms = []
            for g in aggregates:
                group_name = ", ".join("%s: %s" % (k, g['group'][k])
                                       for k in sorted(g['group']))
                for name in g['measures']:
                    for ts, g, value in g['measures'][name]:
                        ms.append((group_name, name, ts.isoformat(), g, value))
            return ('group',) + self.COLS, ms
        return self.COLS, [(name, ts.isoformat(), g, value)
                           for name, measures in aggregates.items()
                           for ts, g, value in measures]
