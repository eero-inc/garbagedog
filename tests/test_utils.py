import datetime
import os
import pytest
import time

from garbagedog.constants import GCEventType, GCSizeInfo

from garbagedog.utils import GCLogHandler
from garbagedog.utils import parse_line_for_sizes, parse_line_for_times


def test_parse_line_for_times():
    log_line = "2015-05-26T14:45:37.987-0200: 151.126: [GC (Allocation Failure) 151.126: " \
               "[DefNew: 629119K->69888K(629120K), 0.0584157 secs] 1619346K->1273247K(2027264K), " \
               "0.0585007 secs] [Times: user=0.06 sys=0.00, real=0.06 secs]"

    event_type, duration = parse_line_for_times(log_line)
    assert event_type == GCEventType.DEF_NEW
    assert duration == 0.06

def test_parse_line_for_times_no_match():
    log_line = "2015-05-26T14:45:37.987-0200: 151.126: Nothing Happened"

    assert parse_line_for_times(log_line) is None

def test_parse_line_for_sizes():
    log_line = "2012-04-04T19:08:23.054+0000: 511001.548: [Full GC 511001.549: [CMS2012-04-04T19:08:48.906+0000: " \
               "511027.400: [CMS-concurrent-preclean: 51.957/52.341 secs] [Times: user=76.72 sys=0.15, " \
               "real=52.34 secs] (concurrent mode failure): 18431999K->16174249K(18432000K), 106.0788490 secs] " \
               "29491199K->16174249K(29491200K), [CMS Perm : 69005K->69005K(115372K)], 106.0801410 secs] " \
               "[Times: user=106.01 sys=0.00, real=106.06 secs]"

    timestamp, size_info = parse_line_for_sizes(log_line)
    assert timestamp == datetime.datetime(2012, 4, 4, 19, 8, 23, 54000, tzinfo=datetime.timezone.utc)
    assert size_info == GCSizeInfo(young_begin_k=29491199,
                                   young_end_k=16174249,
                                   young_total_k=29491200,
                                   whole_heap_begin_k=69005,
                                   whole_heap_end_k=69005,
                                   whole_heap_total_k=115372)

def test_parse_line_for_sizes_no_match():
    log_line = "2015-05-26T14:45:37.987-0200: 151.126: Nothing Happened"

    assert parse_line_for_sizes(log_line) is None

def test_gc_log_handler(tmpdir):

    gc_log = tmpdir.mkdir("logs").join("gc.log.1")
    gc_log.write("")

    with GCLogHandler(os.path.join(str(tmpdir), "logs/")) as gc_log_handler:
        log_line_generator = gc_log_handler.get_log_lines()
        gc_log.write("hello world")
        line = next(log_line_generator)
        assert line == "hello world"

        gc_log.write("foo", mode="a")
        line = next(log_line_generator)
        assert line == "foo"

def test_gc_log_handler_newest_log(tmpdir):

    gc_log = tmpdir.mkdir("logs").join("gc.log.1")
    gc_log.write("")
    time.sleep(1)

    gc_log_2 = tmpdir.join("logs").join("gc.log.2")
    gc_log_2.write("")

    with GCLogHandler(os.path.join(str(tmpdir), "logs/")) as gc_log_handler:
        gc_log.write("foo")
        gc_log_2.write("bar")
        line = next(gc_log_handler.get_log_lines())
        assert line == "bar"
