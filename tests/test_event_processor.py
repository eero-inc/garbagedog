from mock import call, Mock

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

    gc_event_processor._process_line(log_line_2, log_line)

    gc_event_processor.stats.timing.assert_has_calls(
        [
            call('garbagedog_gc_event_duration', 0.06, tags=['stw:True', 'event_type:DefNew'])
        ]
    )
