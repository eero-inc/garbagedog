from codecs import open as codecs_open
from setuptools import setup, find_packages


# Get the long description from the readme
with codecs_open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='garbagedog',
    version='0.0.3',
    description='Parse JVM gc.logs and emit stats over dogstatsd',
    long_description=long_description,
    author='Will Bertelsen',
    author_email='willb@eero.com',
    url='https://github.com/eero-inc/garbagedog',
    license='All rights reserved',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    scripts=[
        'bin/garbagedog'
    ],
    python_requires='>=3.4',
    install_requires=[
        'datadog',
        'typing',
    ],
)
