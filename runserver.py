#!/usr/bin/python

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources
import argparse

parser = argparse.ArgumentParser(
    description='Run the Kernel test harness app')

parser.add_argument(
    '--host', default="127.0.0.1",
    help='Hostname to listen on. When set to 0.0.0.0 the server is available '
    'externally. Defaults to 127.0.0.1 making the it only visible on localhost')

args = parser.parse_args()

from kerneltest.app import APP
APP.debug = True
APP.run(host=args.host)
