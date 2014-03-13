#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import errno
import os
import sys

import dbtools
import generateindex

import mysql.connector
import cgi, cgitb
cgitb.enable()


def parseresults(logfile):
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

def checklogdir(logdir):
    try:
        os.makedirs(logdir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

if __name__ == '__main__':
    logdir = 'logs'
    checklogdir(logdir)
    checklogdir('tmp')
    form = cgi.FieldStorage()
    if form.getvalue("user"):
        tester = form.getvalue("user")
    else:
        tester = 'anon'
    fileitem = form['filename']
    if fileitem.filename:
        # strip leading path from file name to avoid 
        # directory traversal attacks
        fn = os.path.basename(fileitem.filename)
        open('tmp/' + fn, 'wb').write(fileitem.file.read())
        logfile = 'tmp/' + fn

    print "Content-Type: text/html\n"
    testdate, testset, testkver, testrel, testresult, failedtests = parseresults(logfile)
    relarch = testkver.split(".")
    fver = relarch[-2].replace("fc","",1)
    testarch = relarch[-1]
    db = dbtools.dbsetup()
    cursor = db.cursor()
    insert = """
    INSERT INTO kerneltest
        (tester, testdate, testset, kver, fver, testarch, testrel, testresult, failedtests)
        VALUES
        ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');
        """ % (tester, testdate, testset, testkver, fver, testarch, testrel, testresult, failedtests)
    try:
        cursor.execute(insert)
        testid = cursor.lastrowid
        db.commit()
        print "db success"
    except:
        db.rollback()
        print "db fail"
    db.close()
    if 'testid' in locals():
        logdest = logdir + "/" + str(testid) + ".log"
        os.rename(logfile, logdest)
        generateindex.createfiles()
