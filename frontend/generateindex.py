#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import itertools
import sys
import os
import dbtools

from jinja2 import Template


def createfiles():
    ''' Creates all the html files. '''

    # Create the output if it does not already exists
    if not os.path.exists('output'):
        os.mkdir('output')

    session = dbtools.dbsetup()
    webdir = './'
    releases = dbtools.getcurrentreleases(session)
    rawhide = dbtools.getrawhide(session)

    test_matrix = []
    for release in releases:
        arches = dbtools.getarches(session, release)
        for arch in arches:
            results = dbtools.getlatest(session, release, arch)
            test_matrix.append(results)

    try:
        # Read in template
        stream = open('template/index.html', 'r')
        tplfile = stream.read()
        stream.close()

        # Fill the template
        mytemplate = Template(tplfile)
        html = mytemplate.render(
            releases=releases,
            rawhide=rawhide,
            test_matrix=test_matrix,
            date=datetime.datetime.utcnow().strftime("%a %b %d %Y %H:%M")
        )

        # Write down the page
        stream = open('output/index.html', 'w')
        stream.write(html)
        stream.close()
    except IOError, err:
        print 'ERROR: %s' % err

    # Create Fedora Release summaries
    try:
        # Read in template
        stream = open('template/index.html', 'r')
        tplfile = stream.read()
        stream.close()

        for release in releases:
            kernels = dbtools.getkernelsbyrelease(session, release)

            # Fill the template
            mytemplate = Template(tplfile)
            html = mytemplate.render(
                releases=releases,
                rawhide=rawhide,
                release=release,
                kernels=kernels,
                date=datetime.datetime.utcnow().strftime("%a %b %d %Y %H:%M")
            )

            # Write down the page
            stream = open('output/fedora_%s.html' % release.releasenum, 'w')
            stream.write(html)
            stream.close()
    except IOError, err:
        print 'ERROR: %s' % err
    os.link(webdir + "fedora_" + str(rawhide[0]) + ".html", webdir + "rawhide.html")

    # Create kernel summaries
    try:
        # Read in template
        stream = open('template/kernel.html', 'r')
        tplfile = stream.read()
        stream.close()

        for kernel in dbtools.getallkernels(session):
            tests = dbtools.getresultsbykernel(session, kernel)

            # Fill the template
            mytemplate = Template(tplfile)
            html = mytemplate.render(
                releases=releases,
                rawhide=rawhide,
                kernel=kernel,
                tests=tests,
                date=datetime.datetime.utcnow().strftime("%a %b %d %Y %H:%M")
            )

            # Write down the page
            stream = open('output/%s.html' % kernel.kver, 'w')
            stream.write(html)
            stream.close()
    except IOError, err:
        print 'ERROR: %s' % err
