#!/bin/bash
#KERNELTEST_CONFIG=../tests/kerneltest_test.cfg PYTHONPATH=kerneltest nosetests \

PYTHONPATH=kerneltest ./nosetests \
--with-coverage --cover-erase --cover-package=kerneltest $*
