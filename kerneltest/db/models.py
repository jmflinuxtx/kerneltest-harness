# Licensed under the terms of the GNU GPL License version 2

import datetime

import sqlalchemy as sa
from sqlalchemy import Column, Integer, DateTime, String, Text, orm, Boolean, ForeignKey

from .meta import Base, BaseQuery, Session


class Test(Base):
    """
    Represents an individual test within a test suite.

    Attributes:
        id (int): The primary key.
        name (str): The name of the test.
        passed (bool): Whether or not the test passed.
        waived (bool): Whether or not the test is allowed to fail. This is for
            tests that don't reliably pass.
        details (str): A free-form text field containing test details.
        run (TestRun): The test run this test is a part of.
    """

    __tablename__ = "test"
    id = Column(Integer, primary_key=True)
    name = Column(Text, index=True)
    passed = Column(Boolean, index=True)
    waived = Column(Boolean, index=True)
    details = Column(Text)
    run = orm.relationship("TestRun", back_populates="tests")
    run_id = Column(Integer, ForeignKey("test_run.id"))


class TestRun(Base):
    """
    Represents a test run.

    Attributes:
        id (int): The primary key for the test run.
        created (datetime.datetime): The time (in UTC) that the test run was uploaded.
        kernel_version (str): The version string identifying the kernel. For example,
            "5.1.3".
        build_release (str): The "release" field of the RPM. For example,
            "0.rc1.git0.1.fc31" or "300.fc30".
        arch (str): The architecture the tests were run on. For example, "x86_64",
            "ppc64le", or "aarch64".
        user (str): The user who ran the tests. If null, the results were uploaded
            anonymously.
    """

    __tablename__ = "test_run"

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    kernel_version = Column(String(128), nullable=False, index=True)
    build_release = Column(String(256), nullable=False, index=True)
    arch = Column(String(64), nullable=False, index=True)
    user = Column(String(256), nullable=True)
    tests = orm.relationship("Test", back_populates="run")
    release = sa.orm.relationship("Release", back_populates="tests")
    fedora_version = Column(Integer, ForeignKey("release.version"))

    @property
    def package_name(self):
        return "kernel-{}-{}.{}".format(
            self.kernel_version, self.build_release, self.arch
        )

    @property
    def result(self):
        if all([t.passed for t in self.tests]):
            return "PASS"
        elif all([t.passed or t.waived for t in self.tests]):
            return "WARN"
        else:
            return "FAIL"


class ReleaseQuery(BaseQuery):
    def rawhide(self):
        """
        Get the current Rawhide release object.

        Returns:
            Release: The Rawhide release.
        """
        return (
            self.filter_by(support="RAWHIDE").order_by(Release.version.desc()).first()
        )

    def maintained(self):
        """
        Get the list of maintained Fedora releases.

        Returns:
            list of Release: The releases that are not marked retired.
        """
        """ Return the Release information for all active releases. """
        return (
            self.filter(Release.support != "RETIRED")
            .order_by(Release.version.desc())
            .all()
        )


class Release(Base):
    """
    Represents a Fedora release.

    Attributes:
        version (int): The Fedora version (e.g. 27 for Fedora 27).
        support (sa.Enum): An enum that indicates what state the release is in.
    """

    __tablename__ = "release"

    query = Session.query_property(query_cls=ReleaseQuery)

    version = sa.Column(sa.Integer, primary_key=True)
    support = sa.Column(
        sa.Enum("RAWHIDE", "TEST", "RELEASE", "RETIRED", name="support")
    )
    tests = sa.orm.relationship("TestRun", back_populates="release")


def get_stats():
    """ Return a dictionary containing statistics about the data in the
    database.
    """
    output = {}
    session = Session()

    releases = Release.query.maintained()

    output["arches"] = (
        session.query(TestRun.arch)
        .filter(TestRun.fedora_version.in_([r.version for r in releases]))
        .distinct()
        .count()
    )
    output["kernels"] = (
        session.query(TestRun.kernel_version)
        .filter(TestRun.fedora_version.in_([r.version for r in releases]))
        .distinct()
        .count()
    )
    output["n_test"] = TestRun.query.filter(
        TestRun.fedora_version.in_([r.version for r in releases])
    ).count()

    # Tests per release
    rel_stats = {}
    for release in releases:
        tmp = {}
        tmp["tests"] = TestRun.query.filter_by(release=release).count()
        tmp["kernels"] = (
            session.query(TestRun.kernel_version)
            .filter_by(release=release)
            .distinct()
            .count()
        )
        tmp["arches"] = (
            session.query(TestRun.arch).filter_by(release=release).distinct().count()
        )
        tmp["testers"] = (
            session.query(TestRun.user).filter_by(release=release).distinct().count()
        )
        rel_stats[release.version] = tmp
    output["rel_stats"] = rel_stats

    # Tests per kernel
    kernels = [
        k.kernel_version
        for k in session.query(TestRun.kernel_version)
        .filter(TestRun.fedora_version.in_([r.version for r in releases]))
        .distinct()
        .all()
    ]
    ker_stats = {}
    for kernel in kernels:
        tmp = {}
        tmp["releases"] = 1
        tmp["tests"] = TestRun.query.filter_by(kernel_version=kernel).count()
        tmp["arches"] = (
            session.query(TestRun.arch)
            .filter_by(kernel_version=kernel)
            .distinct()
            .count()
        )
        tmp["testers"] = (
            session.query(TestRun.user)
            .filter_by(kernel_version=kernel)
            .distinct(TestRun.user)
            .count()
        )
        ker_stats[kernel] = tmp
    output["ker_stats"] = ker_stats

    return output
