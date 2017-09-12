from garbagedog.constants import GCEventType


def test_from_gc_line():
    log_line = "2015-05-26T14:45:37.987-0200: 151.126: [GC (Allocation Failure) 151.126: [DefNew: " \
               "629119K->69888K(629120K), 0.0584157 secs] 1619346K->1273247K(2027264K), 0.0585007 secs] " \
               "[Times: user=0.06 sys=0.00, real=0.06 secs]"

    assert GCEventType.from_gc_line(log_line) == GCEventType.DEF_NEW

def test_from_gc_line_unknown():
    log_line = "2015-05-26T14:45:37.987-0200 Nothing Here"

    assert GCEventType.from_gc_line(log_line) == GCEventType.UNKNOWN
