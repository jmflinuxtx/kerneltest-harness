#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import mysql.connector

def dbsetup():
    #
    # Configure MySQL login and database to use in config.py
    #
    from dbconfig import Config
    config = Config.dbinfo().copy()
    db = mysql.connector.Connect(**config)
    return db

def getcurrentreleases(cursor):
    query = "SELECT releasenum FROM releases WHERE NOT support='RETIRED' ORDER BY releasenum DESC;"
    cursor.execute(query)
    releases = cursor.fetchall()
    return releases

def getrawhide(cursor):
    query = "SELECT releasenum FROM releases WHERE support='RAWHIDE';"
    cursor.execute(query)
    rawhide = cursor.fetchone()
    return rawhide

def getarches(cursor, release):
    query = "SELECT DISTINCT(testarch) FROM kerneltest WHERE fver= '%s' ORDER BY testarch DESC;" %(release)
    cursor.execute(query)
    arches = cursor.fetchall()
    return arches

def getlatest(cursor, release, arch):
    query = """
    SELECT * FROM kerneltest 
        WHERE testid=(SELECT MAX(testid) FROM kerneltest
        WHERE testarch = "%s" AND fver = "%s" AND tester = "kerneltest" );
        """ % (arch[0], release[0])
    cursor.execute(query)
    results = cursor.fetchone()
    return results

def getkernelsbyrelease(cursor, release):
    query = "SELECT DISTINCT(kver) from kerneltest where fver='%s' ORDER BY kver DESC;" %(release)
    cursor.execute(query)
    kernels = cursor.fetchall()
    return kernels

def getresultsbykernel(cursor, kernel):
    query = """
    SELECT * FROM kerneltest 
        WHERE kver="%s"
        ORDER BY testid;
        """ % (kernel)
    cursor.execute(query)
    tests = cursor.fetchall()
    return tests
