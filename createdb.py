#!/usr/bin/python

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import kerneltest.dbtools as dbtools
import kerneltest.app as app

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
SESSION.flush()

release = dbtools.Release(
    releasenum = "20",
    support = "RELEASE",
)
SESSION.add(release)
SESSION.flush()

release = dbtools.Release(
    releasenum = "21",
    support = "RAWHIDE",
)
SESSION.add(release)
SESSION.flush()
SESSION.commit()

