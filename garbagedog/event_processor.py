from datetime import datetime
import glob
import os
import sys
import time

from datadog.dogstatsd.base import DogStatsd

from .constants import GCEventType, GCSizeInfo
from .constants import ABSOLUTE_TIME_REGEX, RELATIVE_TIME_REGEX, CONFLATED_RELATIVE_REGEX, CONFLATED_ABSOLUTE_REGEX, TIMEFORMAT
from .utils import GCLogHandler
from .utils import parse_line_for_times, parse_line_for_sizes


class GCEventProcessor(object):

    def __init__(self, dogstatsd_host, dogstatsd_port, extra_tags, verbose=False):
        """
        Given a dogstatsd connection, provide an object for processing JVM garbage collector logs and emitting
        relevant events over dogstatsd. GC logs can be input via a log directory or STDIN.

        :param dogstatsd_host: dogstatsd connection host
        :param dogstatsd_port: dogstatsd connection port
        :param extra_tags: dogstatsd constant tags
        :param verbose: If True, print extra info when processing logs
        """
        self.stats = DogStatsd(host=dogstatsd_host, port=dogstatsd_port, constant_tags=extra_tags)
        self.verbose = verbose

        self.last_time_and_size_info = None
        self.last_minor_time = None
        self.last_major_time = None

    def process_log_directory(self, log_directory, glob_pattern="gc.log*", refresh_logfiles_seconds=60, sleep_seconds=1):
        """
        Given a directory of GC logs, generate datadog stats from log lines as they are added to the newest gc* log file

        :param log_directory: Directory of find GC logs
        :param glob_pattern: Pattern to match for garbage collection logs
        :param refresh_logfiles_seconds: How often (in seconds) to check for newer rotated log files
        :param sleep_seconds: How often (in seconds) to poll for new log lines
        """
        with GCLogHandler(log_directory,
                          glob_pattern=glob_pattern,
                          refresh_logfiles_seconds=refresh_logfiles_seconds,
                          sleep_seconds=sleep_seconds,
                          verbose=self.verbose) as log_handler:
            previous_record = ""
            for line in log_handler:
                previous_record = self._process_line(line, previous_record)

    def process_stdin(self):
        """
        Generate datadog stats from log lines from STDIN
        """
        previous_record = ""
        while True:
            inline = sys.stdin.readline()
            if not inline:
                break
            previous_record = self._process_line(inline, previous_record)

    def _process_for_frequency_stats(self, stripped_line: str):
        line_time_match = ABSOLUTE_TIME_REGEX.match(stripped_line)
        if line_time_match:
            line_time = datetime.strptime(line_time_match.group(1), TIMEFORMAT)
            if GCEventType.CMS_INITIAL_MARK.gc_text in stripped_line or GCEventType.FULL_GC.gc_text in stripped_line:
                if self.last_major_time:
                    elapsed = (line_time - self.last_major_time).total_seconds()
                    self.stats.histogram("garbagedog_time_between_old_gc", elapsed)
                self.last_major_time = line_time
            elif GCEventType.PAR_NEW.gc_text in stripped_line or GCEventType.PS_YOUNG_GEN.gc_text in stripped_line:
                if self.last_minor_time:
                    elapsed = (line_time - self.last_minor_time).total_seconds()
                    self.stats.histogram("garbagedog_time_between_young_gc", elapsed)
                self.last_minor_time = line_time

    def _process_eventline(self, stripped_line: str):
        if stripped_line:
            if self.verbose:
                print('.', end='', flush=True)

            self._process_for_frequency_stats(stripped_line)

            time_info = parse_line_for_times(stripped_line)
            if time_info:
                event_type, duration = time_info
                tags = ["stw:{}".format(event_type.is_stop_the_world), "event_type:{}".format(event_type.stats_name)]
                self.stats.timing("garbagedog_gc_event_duration", duration, tags=tags)

            time_and_size_info = parse_line_for_sizes(stripped_line)
            if time_and_size_info:
                timestamp, size_info = time_and_size_info
                if self.last_time_and_size_info:
                    event_time = timestamp
                    last_event_time, last_size_info = self.last_time_and_size_info
                    elapsed = (event_time - last_event_time).total_seconds()
                    bytes_added = size_info.whole_heap_begin_k - last_size_info.whole_heap_end_k
                    self.stats.histogram("garbagedog_allocation_rate_histogram", bytes_added / elapsed)
                self.last_time_and_size_info = (timestamp, size_info)

    def _process_line(self, inline, previous_record):
        stripped_line = inline.rstrip()

        conflated_relative = CONFLATED_RELATIVE_REGEX.match(stripped_line)
        conflated_absolute = CONFLATED_ABSOLUTE_REGEX.match(stripped_line)

        if ABSOLUTE_TIME_REGEX.match(stripped_line) or RELATIVE_TIME_REGEX.match(stripped_line):
            self._process_eventline(previous_record)
            previous_record = stripped_line
        elif conflated_relative:
            previous_record = previous_record + conflated_relative.group(1)
            self._process_eventline(previous_record)
            previous_record = conflated_relative.group(2)
        elif conflated_absolute:
            previous_record = previous_record + conflated_absolute.group(1)
            self._process_eventline(previous_record)
            previous_record = conflated_absolute.group(2)
        else:
            previous_record = previous_record + " " + stripped_line

        return previous_record
