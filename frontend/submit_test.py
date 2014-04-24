#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import argparse
import os
import sys

import dbtools
import generate_reports

def setup_parser():
    ''' Set the main arguments.
    '''
    parser = argparse.ArgumentParser(prog="kernel-test")
    # General connection options
    parser.add_argument('--user', dest="username", default='anon',
                        help="FAS username")
    parser.add_argument('logfile', help="Log file from the tests")
    return parser


def parseresults(logfile):
    ''' Parse the result of the kernel tests. '''
    with open (logfile, 'r') as log:
        for line in log:
            if "Date: " in line:
                testdate = line.replace("Date: ","",1).rstrip('\n')
            elif "Test set: " in line:
                testset = line.replace("Test set: ","",1).rstrip('\n')
            elif "Kernel: " in line:
                testkver = line.replace("Kernel: ","",1).rstrip('\n')
            elif "Release: " in line:
                testrel = line.replace("Release: ","",1).rstrip('\n')
            elif "Result: " in line:
                testresult = line.replace("Result: ","",1).rstrip('\n')
            elif "Failed Tests: " in line:
                failedtests = line.replace("Failed Tests: ","",1).rstrip('\n')
            elif "========" in line:
                break
            else:
                print "No match found for: %s" % (line)
    return testdate, testset, testkver, testrel, testresult, failedtests


def main():
    logdir = 'logs'
    if not os.path.exists(logdir) and not os.path.isdir(logdir):
        os.mkdir(logdir)

    parser = setup_parser()
    # Parse the commandline
    try:
        arg = parser.parse_args()
    except argparse.ArgumentTypeError, err:
        print "\nError: {0}".format(err)
        return 2

    (testdate, testset, testkver, testrel,
     testresult, failedtests) = parseresults(args.logfile)

    relarch = testkver.split(".")
    fver = relarch[-2].replace("fc","",1)
    testarch = relarch[-1]

    session = dbtools.dbsetup()
    test = dbtools.KernelTest(
        tester=args.user,
        testdate=testdate,
        testset=testset,
        kver=kver,
        fver=fver,
        testarch=testarch,
        testrel=testrel,
        testresult=testresult,
        failedtests=failedtests
    )
    try:
        session.add(test)
        session.commit()
        print "db success"

        logdest = logdir + "/" + str(test.testid) + ".log"
        os.rename(logfile, logdest)
        generate_reports.createfiles()

    except:
        session.rollback()
        print "db fail"


if __name__ == '__main__':
    main()
