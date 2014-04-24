#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import datetime

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session

BASE = declarative_base()


class KernelTest(BASE):
    __tablename__ = 'kerneltest'
    testid = sa.Column(sa.Integer, primary_key=True)
    tester = sa.Column(sa.String(20), nullable=False, default='anon')
    testdate = sa.Column(
        sa.String(80), nullable=False, default=datetime.datetime.utcnow)
    testset = sa.Column(sa.String(80), nullable=False)
    kver = sa.Column(sa.Text(), nullable=False)
    fver = sa.Column(sa.Integer, nullable=True)
    testarch = sa.Column(sa.String(8), nullable=False)
    testrel = sa.Column(sa.String(80), nullable=False)
    testresult = sa.Column(sa.Enum('PASS', 'FAIL', name='testresult'))
    failedtests = sa.Column(sa.Text(), nullable=True)
    authenticated = sa.Column(sa.Boolean, nullable=False, default=False)


class Release(BASE):
    __tablename__ = 'releases'
    releasenum = sa.Column(sa.Integer, primary_key=True)
    support = sa.Column(
        sa.Enum('RAWHIDE', 'TEST', 'RELEASE', 'RETIRED', name='support'))


def create_session(
        db_url, debug=False, pool_recycle=3600, create_table=False):
    """ Create the Session object to use to query the database.

    :arg db_url: URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg debug: a boolean specifying wether we should have the verbose
        output of sqlalchemy or not.
    :kwarg create_table: a boolean specifying wether the database should be
        instanciated/created or not.
    :return a Session that can be used to query the database.

    """
    engine = sa.create_engine(
        db_url, echo=debug, pool_recycle=pool_recycle)
    if create_table:
        BASE.metadata.create_all(engine)
    scopedsession = scoped_session(sessionmaker(bind=engine))
    return scopedsession


def dbsetup():
    ''' Return the session connecting to the database. '''
    from dbconfig import Config
    return create_session(Config.db_url())


def getcurrentreleases(session):
    ''' Return the Release information for all active releases. '''
    query = session.query(
        Release
    ).filter(
        Release.support != 'RETIRED'
    ).order_by(
        Release.releasenum.desc()
    )
    return query.all()


def getrawhide(session):
    ''' Return the releasenum for the rawhide releases. '''
    query = session.query(
        Release
    ).filter(
        Release.support == 'RAWHIDE'
    ).order_by(
        Release.releasenum.desc()
    )
    return query.first()


def getarches(session, release):
    ''' Return all distinct arch for the specified release. '''
    query = session.query(
        sa.func.distinct(KernelTest.testarch)
    ).filter(
        KernelTest.fver == release
    ).order_by(
        KernelTest.testarch.desc()
    )
    return query.all()


def getlatest(session, release, arch):
    ''' Return the latest test for the specified release and arch. '''
    query = session.query(
        KernelTest
    ).filter(
        KernelTest.tester == 'kerneltest'
    ).filter(
        KernelTest.fver == release
    ).filter(
        KernelTest.testarch == arch
    ).order_by(
        KernelTest.testid.desc()
    )

    return query.first()


def getkernelsbyrelease(session, release):
    ''' Return the different kernel version for the release specified. '''
    query = session.query(
        sa.func.distinct(KernelTest.kver)
    ).filter(
        KernelTest.fver == release
    ).order_by(
        KernelTest.kver.desc()
    )

    return query.all()


def getresultsbykernel(session, kernel):
    ''' Return test results for the specified kernel version. '''
    query = session.query(
        KernelTest
    ).filter(
        KernelTest.kver == kernel
    ).order_by(
        KernelTest.testid.desc()
    )

    return query.all()


def getallkernels(session):
    ''' Return all kernels present in the database. '''
    query = session.query(
        KernelTest
    ).order_by(
        KernelTest.kver.desc()
    )

    return query.all()
