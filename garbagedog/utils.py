from datetime import datetime
import glob
import os
import sys
import time
from typing import Tuple, Optional, Generator
from typing.io import TextIO

from .constants import GCEventType, GCSizeInfo
from .constants import SIZE_REGEX, TIMES_REGEX, TIMEFORMAT, THREE_ARROWS_REGEX


class GCLogHandler(object):

    def __init__(self,
                 log_directory: str,
                 glob_pattern: str = "gc.log*",
                 refresh_logfiles_seconds: int = 60,
                 sleep_seconds: int = 1,
                 verbose: bool = False) -> None:
        """
        Given a `log_directory`, provide an object for returning new GC logs in that directory. This object can
        be used as a contextmanager for convenience. For example:

            with GCLogHandler('/var/log/gc/') as gc_log_handler:
                for line in gc_log_handler:
                    print(line)

        This log handler object will also handle opening rotated log files when they are created.

        :param log_directory: Directory to find GC logs
        :param glob_pattern: Pattern to match for garbage collection logs
        :param refresh_logfiles_seconds: How often (in seconds) to check for newer rotated log files
        :param sleep_seconds: How often (in seconds) to poll for new log lines
        :param verbose: If True, print extra info when log files are opened
        """
        self.log_directory = log_directory
        self.glob_pattern = glob_pattern
        self.refresh_logfiles_seconds = refresh_logfiles_seconds
        self.sleep_seconds = sleep_seconds
        self.verbose = verbose

        self.log_file_name = None  # type: str
        self.log_file = None  # type: TextIO
        self.last_new_line_seen = datetime.utcfromtimestamp(0)  # type: datetime
        self.previous_record = ""  # type: str

    def __enter__(self):
        self._load_newest_file()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.log_file:
            self.log_file.close()

    def __iter__(self):
        return self.get_log_lines()

    def get_log_lines(self) -> Generator:
        """
        Generator that returns the next log line. If there are no new log lines, this will sleep for `sleep_time` seconds.
        If the log file is not updated after `refresh_logfiles_seconds` and a new log file exists, the new log file will
        be used.

        :return: The next log line in GC logs
        """
        while True:
            current_time = datetime.now()

            # gc.logs rotate, so if we dont see output for a while, we should make sure were reading the newest file
            if (current_time - self.last_new_line_seen).total_seconds() > self.refresh_logfiles_seconds:
                self._load_newest_file()

                if not self.log_file:
                    printv("No logfiles found in {}, sleeping for {} seconds"
                           .format(self.log_directory, self.refresh_logfiles_seconds), self.verbose)
                    time.sleep(self.refresh_logfiles_seconds)
                    continue

            line = self.log_file.readline()
            if line:
                self.last_new_line_seen = current_time
                yield line
            else:
                time.sleep(self.sleep_seconds)

    def _load_newest_file(self) -> None:
        printv("", self.verbose)
        printv("Last line seen {} seconds ago!"
               .format((datetime.now() - self.last_new_line_seen).total_seconds()), self.verbose)

        gc_logs = glob.glob(os.path.join(self.log_directory, self.glob_pattern))

        if gc_logs:
            newest_log_name = max(gc_logs, key=os.path.getctime)
            if newest_log_name != self.log_file_name:
                if self.log_file:
                    self.log_file.close()
                printv("Now reading from: {}!".format(newest_log_name), self.verbose)

                self.log_file = open(newest_log_name)
                self.log_file.seek(0, 2)
                self.log_file_name = newest_log_name
            self.last_new_line_seen = datetime.now()


def parse_line_for_times(line: str) -> Optional[Tuple[GCEventType, float]]:
    """
    Given a log line, return an event type and duration if it exists

    :param line: Log line
    :return: Tuple of (event type, duration)
    """
    time_match = TIMES_REGEX.match(line)
    if time_match:
        gctime_in_seconds = time_match.group(1)
        event_type = GCEventType.from_gc_line(line)
        return event_type, float(gctime_in_seconds)


def parse_line_for_sizes(line: str) -> Optional[Tuple[datetime, GCSizeInfo]]:
    """
    Given a log line, return a timestamp and size info object if it exists

    :param line: Log line
    :return: Tuple of (timestamp, size info object)
    """
    arrows_match = THREE_ARROWS_REGEX.match(line)
    size_match = SIZE_REGEX.match(line)
    if size_match and not arrows_match:
        date_str, _, young_begin_k, young_end_k, young_total_k, whole_heap_begin_k, whole_heap_end_k, whole_heap_total_k = size_match.groups()
        timestamp = datetime.strptime(date_str, TIMEFORMAT)
        size_info = GCSizeInfo(
            young_begin_k=int(young_begin_k),
            young_end_k=int(young_end_k),
            young_total_k=int(young_total_k),
            whole_heap_begin_k=int(whole_heap_begin_k),
            whole_heap_end_k=int(whole_heap_end_k),
            whole_heap_total_k=int(whole_heap_total_k))
        return timestamp, size_info


def printv(line: str, verbose: bool) -> None:
    if verbose:
        print(line)
