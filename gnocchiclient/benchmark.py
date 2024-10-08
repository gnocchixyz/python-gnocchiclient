# -*- coding: utf-8 -*-

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
import argparse
import copyreg
import datetime
import functools
import itertools
import logging
import math
import random
import time
import types

from cliff import show

import futurist

import iso8601

from gnocchiclient import utils
from gnocchiclient.v1 import metric_cli


LOG = logging.getLogger(__name__)


def _pickle_method(m):
    if m.im_self is None:
        return getattr, (m.im_class, m.im_func.func_name)
    else:
        return getattr, (m.im_self, m.im_func.func_name)


copyreg.pickle(types.MethodType, _pickle_method)


def _positive_non_zero_int(argument_value):
    if argument_value is None:
        return None
    try:
        value = int(argument_value)
    except ValueError:
        msg = "%s must be an integer" % argument_value
        raise argparse.ArgumentTypeError(msg)
    if value <= 0:
        msg = "%s must be greater than 0" % argument_value
        raise argparse.ArgumentTypeError(msg)
    return value


class StopWatch:
    def __init__(self):
        self.started_at = time.monotonic()

    def elapsed(self):
        return max(0.0, time.monotonic() - self.started_at)


def measure_job(fn, *args, **kwargs):
    # because we cannot pickle BenchmarkPool class
    sw = StopWatch()
    return fn(*args, **kwargs), sw.elapsed()


class BenchmarkPool(futurist.ProcessPoolExecutor):
    def submit_job(self, times, fn, *args, **kwargs):
        self.sw = StopWatch()
        self.times = times
        return [self.submit(measure_job, fn, *args, **kwargs)
                for i in range(times)]

    def map_job(self, fn, iterable, **kwargs):
        r = []
        self.times = 0
        self.sw = StopWatch()
        for item in iterable:
            r.append(self.submit(measure_job, fn, item, **kwargs))
            self.times += 1
        return r

    def _log_progress(self, verb):
        runtime = self.sw.elapsed()
        done = self.statistics.executed
        rate = done / runtime if runtime != 0 else 0
        LOG.info(
            "%d/%d, "
            "total: %.2f seconds, "
            "rate: %.2f %s/second",
            done, self.times, runtime, rate, verb)

    def wait_job(self, verb, futures):
        while self.statistics.executed != self.times:
            self._log_progress(verb)
            time.sleep(0.2)
        runtime = self.sw.elapsed()
        self._log_progress(verb)
        self.shutdown(wait=True)
        results = []
        latencies = []
        for f in futures:
            try:
                result, latency = f.result()
                results.append(result)
                latencies.append(latency)
            except Exception as e:  # noqa
                LOG.error("Error with %s metric: %s", (verb, e))
        latencies = sorted(latencies)
        return results, runtime, {
            'client workers': self._max_workers,
            verb + ' runtime': "%.2f seconds" % runtime,
            verb + ' runtime (cumulated)': "%.2f seconds" % sum(latencies),
            verb + ' executed': self.statistics.executed,
            verb + ' speed': (
                "%.2f %s/s" % ((self.statistics.executed * self._max_workers /
                                sum(latencies))
                               if runtime != 0 else 0, verb)
            ),
            verb + ' failures': self.statistics.failures,
            verb + ' failures rate': (
                "%.2f %%" % (
                    100 * self.statistics.failures /
                    float(self.statistics.executed)
                )
            ),
            verb + ' latency min': min(latencies),
            verb + ' latency max': max(latencies),
            verb + ' latency mean': sum(latencies) / len(latencies),
            verb + ' latency median': self._percentile(latencies, 0.5),
            verb + ' latency 95%\'ile': self._percentile(latencies, 0.95),
            verb + ' latency 99%\'ile': self._percentile(latencies, 0.99),
            verb + ' latency 99.9%\'ile': self._percentile(latencies, 0.999),

        }

    @staticmethod
    def _percentile(sorted_list, percent):
        # NOTE(sileht): we don't to want depends on numpy
        if not sorted_list:
            return None
        k = (len(sorted_list) - 1) * percent
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        d0 = sorted_list[int(f)] * (c - k)
        d1 = sorted_list[int(c)] * (k - f)
        return d0 + d1


class CliBenchmarkBase(show.ShowOne):
    def get_parser(self, prog_name):
        parser = super(CliBenchmarkBase, self).get_parser(prog_name)
        parser.add_argument("--workers", "-w",
                            default=None,
                            type=_positive_non_zero_int,
                            help="Number of workers to use")
        return parser


class CliBenchmarkMetricShow(CliBenchmarkBase,
                             metric_cli.CliMetricWithResourceID):
    """Do benchmark testing of metric show."""

    def get_parser(self, prog_name):
        parser = super(CliBenchmarkMetricShow, self).get_parser(prog_name)
        parser.add_argument("metric", nargs='+',
                            help="ID or name of the metrics")
        parser.add_argument("--count", "-n",
                            required=True,
                            type=_positive_non_zero_int,
                            help="Number of metrics to get")
        return parser

    def take_action(self, parsed_args):
        pool = BenchmarkPool(parsed_args.workers)
        LOG.info("Getting metrics")
        futures = pool.map_job(utils.get_client(self).metric.get,
                               parsed_args.metric * parsed_args.count,
                               resource_id=parsed_args.resource_id)
        result, runtime, stats = pool.wait_job("show", futures)
        return self.dict2columns(stats)


class CliBenchmarkMetricCreate(CliBenchmarkBase,
                               metric_cli.CliMetricCreateBase):
    """Do benchmark testing of metric creation."""

    def get_parser(self, prog_name):
        parser = super(CliBenchmarkMetricCreate, self).get_parser(prog_name)
        parser.add_argument("--count", "-n",
                            required=True,
                            type=_positive_non_zero_int,
                            help="Number of metrics to create")
        parser.add_argument("--keep", "-k",
                            action='store_true',
                            help="Keep created metrics")
        return parser

    def take_action(self, parsed_args):
        pool = BenchmarkPool(parsed_args.workers)

        LOG.info("Creating metrics")
        futures = pool.submit_job(
            parsed_args.count,
            utils.get_client(self).metric._create_new,
            archive_policy_name=parsed_args.archive_policy_name,
            resource_id=parsed_args.resource_id)
        created_metrics, runtime, stats = pool.wait_job("create", futures)

        if not parsed_args.keep:
            LOG.info("Deleting metrics")
            pool = BenchmarkPool(parsed_args.workers)
            futures = pool.map_job(utils.get_client(self).metric.delete,
                                   [m['id'] for m in created_metrics])
            _, runtime, dstats = pool.wait_job("delete", futures)
            stats.update(dstats)

        return self.dict2columns(stats)


class CliBenchmarkMeasuresAdd(CliBenchmarkBase,
                              metric_cli.CliMeasuresAddBase):
    """Do benchmark testing of adding measurements."""

    def get_parser(self, prog_name):
        parser = super(CliBenchmarkMeasuresAdd, self).get_parser(prog_name)
        parser.add_argument("--count", "-n",
                            required=True,
                            type=_positive_non_zero_int,
                            help="Number of total measures to send")
        parser.add_argument("--batch", "-b",
                            default=1,
                            type=_positive_non_zero_int,
                            help="Number of measures to send in each batch")
        parser.add_argument("--timestamp-start", "-s",
                            default=(
                                datetime.datetime.now(tz=iso8601.iso8601.UTC) -
                                datetime.timedelta(days=365)),
                            type=utils.parse_date,
                            help="First timestamp to use")
        parser.add_argument("--timestamp-end", "-e",
                            default=(
                                datetime.datetime.now(tz=iso8601.iso8601.UTC)),
                            type=utils.parse_date,
                            help="Last timestamp to use")
        parser.add_argument("--wait",
                            default=False,
                            action='store_true',
                            help="Wait for all measures to be processed")
        return parser

    def take_action(self, parsed_args):
        pool = BenchmarkPool(parsed_args.workers)
        LOG.info("Sending measures")

        if parsed_args.timestamp_end <= parsed_args.timestamp_start:
            raise ValueError("End timestamp must be after start timestamp")

        # If batch size is bigger than the number of measures to send, we
        # reduce it to make sure we send something.
        if parsed_args.batch > parsed_args.count:
            parsed_args.batch = parsed_args.count

        start = int(parsed_args.timestamp_start.strftime("%s"))
        end = int(parsed_args.timestamp_end.strftime("%s"))
        count = parsed_args.batch

        if (end - start) < count:
            raise ValueError(
                "The specified time range is not large enough "
                "for the number of points")

        random_values = (random.randint(- 2 ** 32, 2 ** 32)
                         for _ in range(count))
        measures = [{"timestamp": ts, "value": v}
                    for ts, v
                    in zip(
                        range(start,
                              end,
                              (end - start) // count),
                        random_values)]

        times = parsed_args.count // parsed_args.batch
        futures = pool.map_job(functools.partial(
            utils.get_client(self).metric.add_measures,
            parsed_args.metric), itertools.repeat(measures, times),
            resource_id=parsed_args.resource_id)
        _, runtime, stats = pool.wait_job("push", futures)

        stats['measures per request'] = parsed_args.batch
        stats['measures push speed'] = (
            "%.2f push/s" % (
                parsed_args.batch * float(stats['push speed'][:-7])
            )
        )

        if parsed_args.wait:
            sw = StopWatch()
            while True:
                status = utils.get_client(self).status.get()
                remaining = int(status['storage']['summary']['measures'])
                if remaining == 0:
                    stats['extra wait to process measures'] = (
                        "%s seconds" % sw.elapsed()
                    )
                    break
                else:
                    LOG.info(
                        "Remaining measures to be processed: %d",
                        remaining)
                time.sleep(1)

        return self.dict2columns(stats)


class CliBenchmarkMeasuresShow(CliBenchmarkBase,
                               metric_cli.CliMeasuresShow):
    """Do benchmark testing of measurements show."""

    def get_parser(self, prog_name):
        parser = super(CliBenchmarkMeasuresShow, self).get_parser(prog_name)
        parser.add_argument("--count", "-n",
                            required=True,
                            type=_positive_non_zero_int,
                            help="Number of total measures to send")
        return parser

    def take_action(self, parsed_args):
        pool = BenchmarkPool(parsed_args.workers)
        LOG.info("Getting measures")
        futures = pool.submit_job(parsed_args.count,
                                  utils.get_client(self).metric.get_measures,
                                  metric=parsed_args.metric,
                                  resource_id=parsed_args.resource_id,
                                  aggregation=parsed_args.aggregation,
                                  start=parsed_args.start,
                                  stop=parsed_args.stop)
        result, runtime, stats = pool.wait_job("show", futures)
        stats['measures per request'] = len(result[0])
        return self.dict2columns(stats)
