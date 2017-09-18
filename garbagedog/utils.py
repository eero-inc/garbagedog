from datetime import datetime
from typing import Tuple, Optional

from .constants import GCEventType, GCSizeInfo
from .constants import SIZE_REGEX, TIMES_REGEX, TIMEFORMAT, THREE_ARROWS_REGEX


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
