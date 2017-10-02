import time
from pathlib import Path

from mock import call, Mock
from watchdog.observers import Observer

from garbagedog.event_processor import GCEventProcessor


def test_process_line():
    log_line = "2015-05-26T14:45:37.987-0200: 151.126: [GC (Allocation Failure) 151.126: " \
               "[DefNew: 629119K->69888K(629120K), 0.0584157 secs] 1619346K->1273247K(2027264K), " \
               "0.0585007 secs] [Times: user=0.06 sys=0.00, real=0.06 secs]"

    log_line_2 = "2012-04-04T19:08:23.054+0000: 511001.548: [Full GC 511001.549: [CMS2012-04-04T19:08:48.906+0000: " \
                 "511027.400: [CMS-concurrent-preclean: 51.957/52.341 secs] [Times: user=76.72 sys=0.15, " \
                 "real=52.34 secs] (concurrent mode failure): 18431999K->16174249K(18432000K), 106.0788490 secs] " \
                 "29491199K->16174249K(29491200K), [CMS Perm : 69005K->69005K(115372K)], 106.0801410 secs] " \
                 "[Times: user=106.01 sys=0.00, real=106.06 secs]"

    gc_event_processor = GCEventProcessor("localhost", "1234", None)
    gc_event_processor.stats.timing = Mock()
    gc_event_processor.previous_record = log_line

    gc_event_processor._process_line(log_line_2)

    gc_event_processor.stats.timing.assert_has_calls(
        [
            call('garbagedog_gc_event_duration', 0.06, tags=['stw:True', 'event_type:DefNew'])
        ]
    )

def test_gc_log_handler(tmpdir):
    gc_event_processor = GCEventProcessor("localhost", "1234", None)
    gc_event_processor._process_line = Mock()

    gc_log = tmpdir.mkdir("logs").join("gc.log.1")
    path = Path(str(tmpdir), "logs")

    observer = Observer()
    observer.schedule(gc_event_processor, path=str(path), recursive=False)
    observer.start()

    gc_log.write("")
    time.sleep(1)
    gc_log.write("hello world", mode="a")
    time.sleep(1)
    gc_log.write("foo", mode="a")
    time.sleep(1)

    observer.stop()

    gc_event_processor._process_line.assert_has_calls(
        [
            call("hello world"), call("foo")
        ]
    )

def test_gc_log_handler_rotates_logs(tmpdir):
    """
    Verify that the watchdog handler switches to a new log file when logs are rotated
    """
    gc_event_processor = GCEventProcessor("localhost", "1234", None)
    gc_event_processor._process_line = Mock()

    gc_log = tmpdir.mkdir("logs").join("gc.log.1")
    path = Path(str(tmpdir), "logs")

    observer = Observer()
    observer.schedule(gc_event_processor, path=str(path), recursive=False)
    observer.start()

    gc_log.write("")
    time.sleep(1)
    gc_log.write("hello world", mode="a")
    time.sleep(1)

    # Start writing to new file
    new_gc_log = tmpdir.join("logs").join("gc.log.2")
    new_gc_log.write("foo")
    time.sleep(1)

    # At this point, file pointer should be updated to point to the end of gc.log.2
    new_gc_log.write("bar", mode="a")
    time.sleep(1)

    observer.stop()

    gc_event_processor._process_line.assert_has_calls(
        [
            call("hello world"), call("bar")
        ]
    )


def test_gc_log_handler_handles_restart(tmpdir):
    """
    Verify that the watchdog handler reopens a log file if it's rewritten
    """
    gc_event_processor = GCEventProcessor("localhost", "1234", None)
    gc_event_processor._process_line = Mock()

    gc_log = tmpdir.mkdir("logs").join("gc.log.1")
    path = Path(str(tmpdir), "logs")

    observer = Observer()
    observer.schedule(gc_event_processor, path=str(path), recursive=False)
    observer.start()

    gc_log.write("")
    time.sleep(1)
    gc_log.write("hello world", mode="a")
    time.sleep(1)

    # Start writing to beginning of file again
    gc_log.write("foo")
    time.sleep(1)

    # At this point, file pointer should have seek'd to the end of the file
    gc_log.write("bar", mode="a")
    time.sleep(1)

    observer.stop()

    gc_event_processor._process_line.assert_has_calls(
        [
            call("hello world"), call("bar")
        ]
    )
