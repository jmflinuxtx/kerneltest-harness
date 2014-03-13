#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import sys
import os
import mysql.connector
import genpage
import dbtools

def createfiles():
    db = dbtools.dbsetup()
    cursor = db.cursor()
    webdir = './'
    releases = dbtools.getcurrentreleases(cursor)
    rawhide = dbtools.getrawhide(cursor)

    # Create index.html
    with open (webdir + "index.html", 'w') as index:
        saved_stdout = sys.stdout
        sys.stdout = index
        genpage.genheader()
        genpage.gensidebar(releases, rawhide)
        genpage.gencurrent(releases, cursor)
        genpage.genfooter()
        sys.stdout = saved_stdout

    # Create Fedora Release summaries
    for release in releases:
         with open (webdir + "fedora_" + str(release[0]) + ".html", 'w') as relpage:
             saved_stdout = sys.stdout
             sys.stdout = relpage
             genpage.genheader()
             genpage.gensidebar(releases, rawhide)
             genpage.genrelease(release, rawhide,  cursor)
             genpage.genfooter()
             sys.stdout = saved_stdout
    os.link(webdir + "fedora_" + str(rawhide[0]) + ".html", webdir + "rawhide.html")
    db.close()
