#!/usr/bin/env python

import glob
import sys
import time
from datetime import datetime
from enum import Enum

import os
import re
from datadog.dogstatsd.base import DogStatsd
from typing import Tuple, Optional

# These regexes are modified from https://github.com/Netflix-Skunkworks/gcviz, Copyright 2013 Netflix, under APACHE 2.0
three_arrows_regex = re.compile("->.*->.*->", re.MULTILINE)
size_regex = re.compile("^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}[+]0000):"
                        " ([0-9]+[.][0-9]{3}): .* ([0-9]+)K->([0-9]+)K\(([0-9]+)K\).*"
                        " ([0-9]+)K->([0-9]+)K\(([0-9]+)K\)", re.MULTILINE)

absolute_time_regex = re.compile("^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}[+]0000):", re.MULTILINE)
relative_time_regex = re.compile("^[0-9]+[.][0-9]+: ")

conflated_relative_regex = re.compile("(^.*[0-9]+[.][0-9]+ secs])([0-9]+[.][0-9]+: .*$)", re.MULTILINE)
conflated_absolute_regex = re.compile("(^.*)([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.*)", re.MULTILINE)

times_regex = re.compile(".*real=([0-9][0-9]*[.][0-9][0-9]*) secs\]\s*", re.MULTILINE)

timeformat = "%Y-%m-%dT%H:%M:%S.%f%z"


class GCEventType(Enum):
    Unknown = 0
    FullGC = 1
    concurrent_mode_failure = 2
    promotion_failed = 3
    ParNew = 4
    CMS_initial_mark = 5
    CMS_concurrent_mark = 6
    CMS_concurrent_abortable_preclean = 7
    CMS_concurrent_preclean = 8
    CMS_remark = 9
    CMS_concurrent_sweep = 10
    CMS_concurrent_reset = 11
    PSYoungGen = 12
    DefNew = 13


def is_stop_the_world(event_type: GCEventType) -> bool:
    return event_type in [GCEventType.FullGC,
                          GCEventType.CMS_initial_mark,
                          GCEventType.CMS_remark,
                          GCEventType.concurrent_mode_failure,
                          GCEventType.promotion_failed,
                          GCEventType.ParNew,
                          GCEventType.PSYoungGen,
                          GCEventType.DefNew]


class GCSizeInfo:
    def __init__(self, young_begin_k: str, young_end_k: str, young_total_k: str,
                 whole_heap_begin_k: str, whole_heap_end_k: str, whole_heap_total_k: str) -> None:
        self.young_begin_k = int(young_begin_k)
        self.young_end_k = int(young_end_k)
        self.young_total_k = int(young_total_k)
        self.whole_heap_begin_k = int(whole_heap_begin_k)
        self.whole_heap_end_k = int(whole_heap_end_k)
        self.whole_heap_total_k = int(whole_heap_total_k)


def process_line_for_sizes(line: str) -> Optional[Tuple[datetime, GCSizeInfo]]:
    arrows_match = three_arrows_regex.match(line)
    size_match = size_regex.match(line)
    if arrows_match:
        return None
    elif size_match:
        date_str, \
            secs_since_jvm_boot, \
            young_begin_k, \
            young_end_k, \
            young_total_k,\
            whole_heap_begin_k, \
            whole_heap_end_k, \
            whole_heap_total_k = size_match.groups()
        timestamp = datetime.strptime(date_str, timeformat)
        size_info = GCSizeInfo(
            young_begin_k=young_begin_k,
            young_end_k=young_end_k,
            young_total_k=young_total_k,
            whole_heap_begin_k=whole_heap_begin_k,
            whole_heap_end_k=whole_heap_end_k,
            whole_heap_total_k=whole_heap_total_k)
        return timestamp, size_info
    return None


def process_line_for_times(line: str) -> Optional[Tuple[GCEventType, float]]:
    time_match = times_regex.match(line)
    if time_match:
        gctime_in_seconds = time_match.group(1)
        event_type = classify_gc_event_type_for_size(line)
        return event_type, float(gctime_in_seconds)

    return None


def classify_gc_event_type_for_size(line: str) -> GCEventType:
    if "Full GC" in line:
        return GCEventType.FullGC
    if "(concurrent mode failure)" in line:
        return GCEventType.concurrent_mode_failure
    if "(promotion failed)" in line:
        return GCEventType.concurrent_mode_failure
    if "ParNew" in line:
        return GCEventType.ParNew
    if "CMS-initial-mark" in line:
        return GCEventType.CMS_initial_mark
    if "CMS-concurrent-mark" in line:
        return GCEventType.CMS_concurrent_mark
    if "CMS-concurrent-abortable-preclean" in line:
        return GCEventType.CMS_concurrent_abortable_preclean
    if "CMS-concurrent-preclean" in line:
        return GCEventType.CMS_concurrent_preclean
    if "CMS-remark" in line:
        return GCEventType.CMS_remark
    if "CMS-concurrent-sweep" in line:
        return GCEventType.CMS_concurrent_sweep
    if "CMS-concurrent-reset" in line:
        return GCEventType.CMS_concurrent_reset
    if "PSYoungGen" in line:
        return GCEventType.PSYoungGen
    if "DefNew" in line:
        return GCEventType.DefNew
    return GCEventType.Unknown


class GCEventProcessor:
    def __init__(self, dogstatsd_host, dogstatsd_port, extra_tags, verbose):
        self.stats = DogStatsd(host=dogstatsd_host, port=dogstatsd_port, constant_tags=extra_tags)
        self.last_size_info = None
        self.last_minor_time = None
        self.last_major_time = None
        self.verbose = verbose

    def process_for_frequency_stats(self, stripped_line: str):
        line_time_match = absolute_time_regex.match(stripped_line)
        if line_time_match:
            line_time = datetime.strptime(line_time_match.group(1), timeformat)
            if "CMS-initial-mark" in stripped_line or "Full GC" in stripped_line:
                if self.last_major_time:
                    elapsed = (line_time - self.last_major_time).total_seconds()
                    self.stats.histogram("garbagedog_time_between_old_gc", elapsed)
                self.last_major_time = line_time
            elif "ParNew" in stripped_line or "PSYoungGen" in stripped_line:
                if self.last_minor_time:
                    elapsed = (line_time - self.last_minor_time).total_seconds()
                    self.stats.histogram("garbagedog_time_between_young_gc", elapsed)
                self.last_minor_time = line_time

    def process_eventline(self, stripped_line: str):
        if stripped_line is not "":
            if self.verbose:
                print('.', end='', flush=True)

            self.process_for_frequency_stats(stripped_line)

            time_info = process_line_for_times(stripped_line)
            if time_info:
                is_stw = is_stop_the_world(time_info[0])
                tags = ["stw:{}".format(is_stw), "event_type:{}".format(time_info[0].name)]
                self.stats.timing("garbagedog_gc_event_duration", time_info[1], tags=tags)

            size_info = process_line_for_sizes(stripped_line)
            if size_info:
                if self.last_size_info:
                    event_time = size_info[0]
                    last_event_time = self.last_size_info[0]
                    elapsed = (event_time - last_event_time).total_seconds()
                    bytes_added = size_info[1].whole_heap_begin_k - self.last_size_info[1].whole_heap_end_k
                    mbps = float(bytes_added) / float(elapsed)
                    self.stats.histogram("garbagedog_allocation_rate_histogram", mbps)
                self.last_size_info = size_info


def get_newest_log(log_dir: str) -> str:
    gc_logs = list(glob.iglob(os.path.join(log_dir, 'gc*')))

    if len(gc_logs) == 0:
        print("No gc logs found in {}".format(log_dir))
        sys.exit(1)

    return max(gc_logs, key=os.path.getctime)


def process_line(processor, inline, previous_record):
    stripped_line = inline.rstrip('\n')

    conflated_relative = conflated_relative_regex.match(stripped_line)
    conflated_absolute = conflated_absolute_regex.match(stripped_line)

    if absolute_time_regex.match(stripped_line) or relative_time_regex.match(stripped_line):
        processor.process_eventline(previous_record)
        previous_record = stripped_line
    elif conflated_relative:
        previous_record = previous_record + conflated_relative.group(1)
        processor.process_eventline(previous_record)
        previous_record = conflated_relative.group(2)
    elif conflated_absolute:
        previous_record = previous_record + conflated_absolute.group(1)
        processor.process_eventline(previous_record)
        previous_record = conflated_absolute.group(2)
    else:
        previous_record = previous_record + " " + stripped_line

    return previous_record


def from_log_dir(
        log_directory,
        dogstatsd_host,
        dogstatsd_port,
        extra_tags=None,
        verbose=False,
        refresh_logfiles_seconds=60,
        sleep_seconds=1) -> None:

    processor = GCEventProcessor(dogstatsd_host, dogstatsd_port, extra_tags, verbose)

    previous_record = ""
    last_new_line_seen = datetime.utcfromtimestamp(0)
    log_file = None

    try:
        while True:
            # gc.logs rotate, so if we dont see output for a while, we should make sure were reading the newest file
            if (datetime.now() - last_new_line_seen).total_seconds() > refresh_logfiles_seconds:
                print('')
                if verbose:
                    print("Last line seen {} seconds ago!"
                          .format((datetime.now() - last_new_line_seen).total_seconds()))
                if log_file:
                    log_file.close()
                newest_log = get_newest_log(log_directory)
                if verbose:
                    print("Now reading from: {}!".format(newest_log))

                log_file = open(newest_log)
                log_file.seek(0, 2)  # seek to EOF
                last_new_line_seen = datetime.now()

            line = log_file.readline()

            if not line:
                time.sleep(sleep_seconds)
                continue
            else:
                last_new_line_seen = datetime.now()
                previous_record = process_line(processor, line, previous_record)
    finally:
        if log_file:
            log_file.close()


def from_stdin(dogstatsd_host, dogstatsd_port, extra_tags=None, verbose=False):
    processor = GCEventProcessor(dogstatsd_host, dogstatsd_port, extra_tags, verbose)
    previous_record = ""
    while True:
        inline = sys.stdin.readline()
        if not inline:
            break
        previous_record = process_line(processor, inline, previous_record)
