#!/usr/bin/python

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import dbtools
import app

dbtools.create_session(
    app.APP.config['DB_URL'],
    debug=True,
    create_table=True)
