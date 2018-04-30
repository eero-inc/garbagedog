from setuptools import setup, find_packages

setup(
    name='garbagedog',
    version='0.0.11',
    description='Parse JVM gc.logs and emit stats over dogstatsd',
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
