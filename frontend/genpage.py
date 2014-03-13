#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import dbtools
import urllib

def genheader():
    print "<html>"
    print "<head>"
    print "<title>Kernel Test Results </title>"
    print "<link rel='stylesheet' type='text/css' href='http://fedoraproject.org/static/css/fedora.css' />"
    print "</head>"
    print "<body>"
    print "<div id='head h1 a'>"
    print "            <img src='http://fedoraproject.org/w/uploads/3/3c/Fedora_logo.png'>"
    print "</div>"

def genfooter():
    print "</body>"
    print "</html>"

def gensidebar(releases, rawhide):
    print "<div id='nav'>"
    print "<a href='index.html'>Home</a>"
    for release in releases:
        if release == rawhide:
            print "<a href='rawhide.html'>Fedora Rawhide</a>"
        else:
            print "<a href='fedora_%s.html'>Fedora %s</a>" %(release[0], release[0])
    print "</div>"

def gencurrent(releases, cursor):
    print "<div id='content'>"
    print "<a href='http://fedoraproject.org/wiki/KernelTestingInitiative'><h1>Fedora Kernel Test Results</h1></a>"
    print "<table border='1' style='width:400px'>"
    print "<tr>"
    print "<th>Kernel</th>"
    print "<th>Result</th>"
    print "<th>Logs</th>"
    print "</tr>"
    for release in releases:
        arches = dbtools.getarches(cursor, release)
        for arch in arches:
            results = dbtools.getlatest(cursor, release, arch)
            logs = "logs/%s.log" %(results[0])
            kver = results[4]
            testresult = results[8]
            print "<tr>"
            print "<td><a href='kernelresult.py?kver=%s'>%s</a></td>"  %(urllib.quote(kver), kver)
            print "<td>%s</td>" %(testresult)
            print "<td><a href='%s'>logs</a></td>" %(logs)
            print "</tr>"
    print "</table>"
    print "</div>"


def genrelease(release, rawhide, cursor):
    print "<div id='content'>"
    if release == rawhide:
        print "<h1>Kernels Tested for Fedora Rawhide</h1>"
    else:
        print "<h1>Kernels Tested for Fedora %s</h1>" %(release)
    print "<table border='1' style='width:400px'>"
    print "<tr>"
    print "<th>Kernel</th>"
    print "</tr>"
    kernels = dbtools.getkernelsbyrelease(cursor,release)
    for kernel in kernels:
            print "<tr>"
            print "<td><a href='kernelresult.py?kver=%s'>%s</a></td>" %(urllib.quote(kernel[0]), kernel[0])
            print "</tr>"
    print "</table>"

def showkernel(kernel, cursor):
    print "<div id='content'>"
    print "<h1>Results for kernel %s</h1>" %(kernel)
    print "<table border='1' style='width:400px'>"
    print "<tr>"
    print "<th>Kernel</th>"
    print "<th>Result</th>"
    print "<th>log</th>"
    print "</tr>"
    tests = dbtools.getresultsbykernel(cursor, kernel)
    for test in tests:
        logs = "logs/%s.log" %(test[0])
        kver = test[4]
        testresult = test[8]
        print "<tr>"
        print "<td>%s</td>" %(kernel)
        print "<td>%s</td>" %(testresult)
        print "<td><a href='%s'>logs</a></td>" %(logs)
        print "</tr>"
    print "</table>"
    print "</div>"
