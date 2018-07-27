# garbagedog
Tail a JVM gc.log and emit stats over the dogstatsd wire format.

`garbagedog` monitors JVM gc logs and emits stats over the dogstatsd wire format.
Normally, these will be recieved by a local agent such as telegraf or datadog-agent.

You can use these stats to monitor continuously monitor your GC performance (though tuning is probably better left to more comprehensive tools).

Parsing logic based on https://github.com/Netflix-Skunkworks/gcviz

## Installation

Requires python 3.4

`pip3 install git+ssh://git@github.com/eero-inc/garbagedog.git#egg=garbagedog`


## JVM Setup
Run your JVM app with the following flags:
```
-Xloggc:/var/log/eero/gc.log
-XX:+UseGCLogFileRotation
-XX:GCLogFileSize=64M
-XX:NumberOfGCLogFiles=2
-XX:+PrintGCDetails
-XX:+PrintGCDateStamps
-XX:+PrintGCApplicationConcurrentTime
-XX:+PrintGCApplicationStoppedTime
-XX:+PrintTenuringDistribution
-XX:+PrintPromotionFailure
-XX:+PrintHeapAtGC
-XX:+PrintGCCause
```

## Usage
```
usage: garbagedog --log-dir /var/log/eero/

Parse JVM gc.logs and emit stats over dogstatsd

optional arguments:
  -h, --help            show this help message and exit
  --tags TAGS           Extra datadog tags, comma separated; ie
                        "application:actorcluster, version:2017.07.27"
  --dogstatsd-host DOGSTATSD_HOST
                        dogstatsd host (default: localhost)
  --dogstatsd-port DOGSTATSD_PORT
                        dogstatsd port (default: 8125)
  --verbose             Emit noisy messages on stdout
  --log-dir LOG_DIR     Read from this log dir instead of stdin
  --glob-pattern GLOB_PATTERN
                        Glob pattern to select gc.log files (default: gc.log*)
  --refresh-logfiles-seconds REFRESH_LOGFILES_SECONDS
                        How often to recheck --log-dir if there are no
                        logfiles found or no new loglines have been written
                        (default: 60)
  --sleep-seconds SLEEP_SECONDS
                        How long to sleep between checking the logfile for new
                        lines (default: 1)
```

## Stats

Timing by event type: `garbagedog_gc_event_duration`

Allocation rate: `garbagedog_allocation_rate_histogram`

Promotion rate: `garbagedog_promotion_rate_histogram`

Old gen GC frequency: `garbagedog_time_between_old_gc`

Young gen GC frequency: `garbagedog_time_between_young_gc`

## Grafana Examples
Example Graphs
![Grafana Graph Example](grafana-examples/grafana.png?raw=true "Grafana Graph Example")

[See grafana json](grafana-examples/grafana-example.json)
## Development

```
git clone git@github.com:eero-inc/garbagedog.git
cd garbagedog
virtualenv --python=python3 ENV
source ENV/bin/activate
pip install -e .
```

## Testing

```
git clone git@github.com:eero-inc/garbagedog.git
cd garbagedog
virtualenv --python=python3 ENV
source ENV/bin/activate
pip install -r dev_requirements.txt

./test.sh
pytest
```


## Building a standalone executable pex
On your targeted environment check out the source and build
```
git clone git@github.com:eero-inc/garbagedog.git
cd garbagedog
virtualenv --python=python3 ENV
source ENV/bin/activate
pip install pex
./build.sh

```

## About
Made for eero Hack Week 2017 - ps we're hiring! https://eero.com/jobs
