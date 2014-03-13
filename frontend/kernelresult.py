#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import mysql.connector
import genpage
import dbtools
import cgi, cgitb
cgitb.enable()

form = cgi.FieldStorage()
kernel = form.getvalue('kver')

print "Content-Type: text/html;charset=utf-8"
print

db = dbtools.dbsetup()
cursor = db.cursor()
releases = dbtools.getcurrentreleases(cursor)
rawhide = dbtools.getrawhide(cursor)

genpage.genheader()
genpage.gensidebar(releases, rawhide)
genpage.showkernel(kernel, cursor)
genpage.genfooter()
db.close()
