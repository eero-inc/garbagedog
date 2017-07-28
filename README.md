# garbagedog
Tail a JVM gc.log and emit stats over dogstatsd.


Parsing logic based on https://github.com/Netflix-Skunkworks/gcviz

## Installation

Requires python 3.4

`pip3 install git+ssh://git@github.com/eero-inc/garbagedog.git#egg=garbagedog`


## Usage
```
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
```

Made for eero Hack Week 2017 - ps we're hiring! https://eero.com/jobs


## Development

```
git clone git@github.com:eero-inc/garbagedog.git
cd garbagedog
virtualenv --python=python3 ENV
source ENV/bin/activate
pip install -e .
```

## Building an executable pex
On your targeted environment check out the source and build
```
git clone git@github.com:eero-inc/garbagedog.git
cd garbagedog
virtualenv --python=python3 ENV
source ENV/bin/activate
pip install pex
./build.sh

```
