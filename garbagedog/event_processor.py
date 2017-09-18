from datetime import datetime
from pathlib import Path
import sys
import time
from typing import Tuple, Optional, List
from typing.io import TextIO

from datadog.dogstatsd.base import DogStatsd
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, DirModifiedEvent, FileSystemEvent

from .constants import GCEventType, GCSizeInfo
from .constants import ABSOLUTE_TIME_REGEX, RELATIVE_TIME_REGEX, CONFLATED_RELATIVE_REGEX, CONFLATED_ABSOLUTE_REGEX, TIMEFORMAT
from .utils import parse_line_for_times, parse_line_for_sizes, printv


class GCEventProcessor(FileSystemEventHandler):

    def __init__(self,
                 dogstatsd_host: str,
                 dogstatsd_port: str,
                 extra_tags: Optional[List[str]],
                 verbose: bool = False,
                 glob_pattern: str = "gc.log*") -> None:
        """
        Given a dogstatsd connection, provide an object for processing JVM garbage collector logs and emitting
        relevant events over dogstatsd. GC logs can be input via a log directory or STDIN.

        :param dogstatsd_host: dogstatsd connection host
        :param dogstatsd_port: dogstatsd connection port
        :param extra_tags: dogstatsd constant tags
        :param verbose: If True, print extra info when processing logs
        :param glob_pattern: Pattern to find log files
        """
        self.stats = DogStatsd(host=dogstatsd_host, port=dogstatsd_port, constant_tags=extra_tags)
        self.verbose = verbose
        self.glob_pattern = glob_pattern

        self.last_time_and_size_info = None  # type: Optional[Tuple[datetime, GCSizeInfo]]
        self.last_minor_time = None  # type: datetime
        self.last_major_time = None  # type: datetime
        self.previous_record = ""  # type: str

        self.log_file = None  # type: TextIO
        self.log_file_path = None  # type: Path

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Overriden watchdog method in FileSystemEventHandler

        Handle created events from the filesystem
        """
        path = Path(event.src_path)
        if not path.match(self.glob_pattern):
            return

        # A new log file has been created, start reading from it
        self._open_file(path, from_beginning=True)
        printv("Now reading from: {}!".format(path), self.verbose)
        line = self.log_file.readline()
        if line:
            self._process_line(line)

    def on_modified(self, event: FileSystemEvent) -> None:
        """
        Overriden watchdog method in FileSystemEventHandler

        Handle modified events from the filesystem
        """
        if isinstance(event, FileModifiedEvent):
            path = Path(event.src_path)
            if not path.match(self.glob_pattern):
                return

            if self.log_file_path != path:
                # An existing, unopened log file has been written to, open it and start reading from the end
                self._open_file(path)
                printv("Now reading from: {}!".format(path), self.verbose)
            else:
                # The currently opened log file has been written to, read the next line
                line = self.log_file.readline()
                if line:
                    self._process_line(line)
                else:
                    # Nothing was read, re-open the log file and start reading from the beginning
                    self._open_file(path, from_beginning=True)
                    printv("Going to beginning of: {}!".format(path), self.verbose)
                    line = self.log_file.readline()
                    if line:
                        self._process_line(line)

    def process_stdin(self) -> None:
        """
        Generate datadog stats from log lines from STDIN
        """
        self.previous_record = ""
        while True:
            inline = sys.stdin.readline()
            if not inline:
                break
            previous_record = self._process_line(inline)

    def _open_file(self, path: Path, from_beginning: bool = False) -> None:
        if self.log_file:
            self.log_file.close()
        self.log_file = open(path)
        self.log_file_path = path
        if not from_beginning:
            self.log_file.seek(0, 2)

    def _process_for_frequency_stats(self, stripped_line: str) -> None:
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

    def _process_eventline(self, stripped_line: str) -> None:
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

    def _process_line(self, inline: str) -> str:
        stripped_line = inline.rstrip()

        conflated_relative = CONFLATED_RELATIVE_REGEX.match(stripped_line)
        conflated_absolute = CONFLATED_ABSOLUTE_REGEX.match(stripped_line)

        if ABSOLUTE_TIME_REGEX.match(stripped_line) or RELATIVE_TIME_REGEX.match(stripped_line):
            self._process_eventline(self.previous_record)
            self.previous_record = stripped_line
        elif conflated_relative:
            self.previous_record = self.previous_record + conflated_relative.group(1)
            self._process_eventline(self.previous_record)
            self.previous_record = conflated_relative.group(2)
        elif conflated_absolute:
            self.previous_record = self.previous_record + conflated_absolute.group(1)
            self._process_eventline(self.previous_record)
            self.previous_record = conflated_absolute.group(2)
        else:
            self.previous_record = self.previous_record + " " + stripped_line

        return self.previous_record
