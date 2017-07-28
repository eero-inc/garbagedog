# garbagedog
Tail a JVM gc.log and emit stats over dogstatsd.


Parsing logic based on https://github.com/Netflix-Skunkworks/gcviz


## Usage
usage: tail -f `ls  -rt  /var/log/eero/gc* | tail -n 1` | garbagedog

Send GC stats over dogstatsd

optional arguments:
  -h, --help            show this help message and exit
  --tags TAGS           Extra datadog tags, comma separated; ie
                        "application:actorcluster, version:7017.07.27"
  --dogstatsd-host DOGSTATSD_HOST
                        dogstatsd host (default=localhost)
  --dogstatsd-port DOGSTATSD_PORT
                        dogstatsd port (default=8125)
