from collections import namedtuple
from enum import Enum
import re


# These regexes are modified from https://github.com/Netflix-Skunkworks/gcviz, Copyright 2013 Netflix, under APACHE 2.0
THREE_ARROWS_REGEX = re.compile("->.*->.*->", re.MULTILINE)
SIZE_REGEX = re.compile("^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}[+]0000):"
                        " ([0-9]+[.][0-9]{3}): .* ([0-9]+)K->([0-9]+)K\(([0-9]+)K\).*"
                        " ([0-9]+)K->([0-9]+)K\(([0-9]+)K\)", re.MULTILINE)

ABSOLUTE_TIME_REGEX = re.compile("^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}[+]0000):", re.MULTILINE)
RELATIVE_TIME_REGEX = re.compile("^[0-9]+[.][0-9]+: ")

CONFLATED_RELATIVE_REGEX = re.compile("(^.*[0-9]+[.][0-9]+ secs])([0-9]+[.][0-9]+: .*$)", re.MULTILINE)
CONFLATED_ABSOLUTE_REGEX = re.compile("(^.*)([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.*)", re.MULTILINE)

TIMES_REGEX = re.compile(".*real=([0-9][0-9]*[.][0-9][0-9]*) secs\]\s*", re.MULTILINE)

TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"


GCSizeInfo = namedtuple(
    "GCSizeInfo", "young_begin_k, young_end_k, young_total_k, whole_heap_begin_k, whole_heap_end_k, whole_heap_total_k")


class GCEventType(Enum):
    UNKNOWN = ("Unknown")
    FULL_GC = ("FullGC", "Full GC", True)
    CONCURRENT_MODE_FAILURE = ("concurrent_mode_failure", "(concurrent mode failure", True)
    PROMOTION_FAILED = ("promotion_failed", "(promotion failed)", True)
    PAR_NEW = ("ParNew", "ParNew", True)
    CMS_INITIAL_MARK = ("CMS_initial_mark", "CMS-initial-mark", True)
    CMS_CONCURRENT_MARK = ("CMS_concurrent_mark", "CMS-concurrent-mark", False)
    CMS_CONCURRENT_ABORTABLE_PRECLEAN = ("CMS_concurrent_abortable_preclean", "CMS-concurrent-abortable-preclean", False)
    CMS_CONCURRENT_PRECLEAN = ("CMS_concurrent_preclean", "CMS-concurrent-preclean", False)
    CMS_REMARK = ("CMS_remark", "CMS-remark", True)
    CMS_CONCURRENT_SWEEP = ("CMS_concurrent_sweep", "CMS-concurrent-sweep", False)
    CMS_CONCURRENT_RESET = ("CMS_concurrent_reset", "CMS-concurrent-reset", False)
    PS_YOUNG_GEN = ("PSYoungGen", "PSYoungGen", True)
    DEF_NEW = ("DefNew", "DefNew", True)

    def __init__(self, stats_name, gc_text=None, is_stop_the_world=False):
        self.stats_name = stats_name
        self.gc_text = gc_text
        self.is_stop_the_world = is_stop_the_world

    @classmethod
    def from_gc_line(cls, line):
        """
        Given a GC log line, return the appropriate event type classification

        :param line: Log line
        :return: GC event type
        """
        for gc_type in cls:
            if gc_type.gc_text and gc_type.gc_text in line:
                return gc_type
        return cls.UNKNOWN
