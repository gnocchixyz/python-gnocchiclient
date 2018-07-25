# -*- encoding: utf-8 -*-
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
from dateutil import tz

import iso8601

import six
from six.moves.urllib import parse as urllib_parse


def add_query_argument(cmd, parser, *args, **kwargs):
    return parser.add_argument(
        cmd,
        help=u"A query to filter resource. "
        u"The syntax is a combination of attribute, operator and value. "
        u"For example: id=90d58eea-70d7-4294-a49a-170dcdf44c3c would filter "
        u"resource with a certain id. More complex queries can be built, "
        u"e.g.: not (flavor_id!=\"1\" and memory>=24). "
        u"Use \"\" to force data to be interpreted as string. "
        u"Supported operators are: not, and, ∧ or, ∨, >=, <=, !=, >, <, =, "
        u"==, eq, ne, lt, gt, ge, le, in, like, ≠, ≥, ≤, like, in.",
        *args, **kwargs)


def list2cols(cols, objs):
    return cols, [tuple([o[k] for k in cols])
                  for o in objs]


def format_string_list(l):
    return ", ".join(l)


def format_dict_list(l):
    return "\n".join(
        "- " + ", ".join("%s: %s" % (k, v)
                         for k, v in elem.items())
        for elem in l)


def format_dict_dict(value):
    return "\n".join(
        "- %s: " % name + " , ".join("%s: %s" % (k, v)
                                     for k, v in elem.items())
        for name, elem in value.items())


def format_move_dict_to_root(obj, field):
    for attr in obj[field]:
        obj["%s/%s" % (field, attr)] = obj[field][attr]
    del obj[field]


def format_resource_type(rt):
    format_move_dict_to_root(rt, "attributes")
    for key in rt:
        if key.startswith("attributes"):
            rt[key] = ", ".join(
                "%s=%s" % (k, v) for k, v in sorted(rt[key].items()))


def format_archive_policy(ap):
    ap['definition'] = format_dict_list(ap['definition'])
    ap['aggregation_methods'] = format_string_list(ap['aggregation_methods'])


def format_resource_for_metric(metric):
    # NOTE(sileht): Gnocchi < 2.0
    if 'resource' not in metric:
        return

    if not metric['resource']:
        metric['resource/id'] = None
        del metric['resource']
    else:
        format_move_dict_to_root(metric, "resource")


def dict_from_parsed_args(parsed_args, attrs):
    d = {}
    for attr in attrs:
        value = getattr(parsed_args, attr)
        if value is not None:
            d[attr] = value
    return d


def dict_to_querystring(objs):
    strings = []
    for k, values in sorted(objs.items()):
        if values is not None:
            if not isinstance(values, (list, tuple)):
                values = [values]
            strings.append("&".join(
                ("%s=%s" % (k, v)
                 for v in map(urllib_parse.quote,
                              map(six.text_type, values)))))
    return "&".join(strings)


def get_pagination_options(parsed_args):
    options = dict(
        sorts=parsed_args.sort,
        limit=parsed_args.limit,
        marker=parsed_args.marker)

    if hasattr(parsed_args, 'details'):
        options['details'] = parsed_args.details
    if hasattr(parsed_args, 'history'):
        options['history'] = parsed_args.history
    return options


def build_pagination_options(details=False, history=False,
                             limit=None, marker=None, sorts=None):
    options = {}
    if details:
        options["details"] = "true"
    if history:
        options["history"] = "true"
    if limit:
        options["limit"] = int(limit)
    if marker:
        options["marker"] = marker
    if sorts:
        options["sort"] = sorts
    return options


def get_client(obj):
    if hasattr(obj.app, 'client_manager'):
        # NOTE(sileht): cliff objects loaded by OSC
        return obj.app.client_manager.metric
    else:
        # TODO(sileht): Remove this when OSC is able
        # to install the gnocchi client binary itself
        return obj.app.client


LOCAL_TIMEZONE = tz.gettz()


def parse_date(s):
    """Parse date from string.

    If no timezone is specified, default is assumed to be local time zone.

    :param s: The date to parse.
    :type s: str
    """
    return iso8601.parse_date(s, LOCAL_TIMEZONE)


def dt_to_localtz(d):
    return d.astimezone(LOCAL_TIMEZONE)
