#!/usr/bin/python

from __future__ import print_function

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

from sqlalchemy.exc import SQLAlchemyError
import kerneltest.app as app
import kerneltest.dbtools as dbtools

dbtools.create_session(
    app.APP.config['DB_URL'],
    debug=True,
    create_table=True)

## Add current supported releases
SESSION=dbtools.create_session(
    app.APP.config['DB_URL'],
    debug=True)

release = dbtools.Release(
    releasenum = "19",
    support = "RELEASE",
)
SESSION.add(release)

release = dbtools.Release(
    releasenum = "20",
    support = "RELEASE",
)
SESSION.add(release)

release = dbtools.Release(
    releasenum = "21",
    support = "RAWHIDE",
)
SESSION.add(release)

try:
    SESSION.commit()
except SQLAlchemyError as err:
    print(err)
