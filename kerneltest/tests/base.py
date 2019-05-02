"""Base test class and utilities for testing."""
from contextlib import contextmanager
import copy
import os
import unittest

from flask import request_started, g
from sqlalchemy import event

from kerneltest import db, app, default_config

engine = None
PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DEFAULT_DB = "sqlite:///" + os.path.join(PROJECT_PATH, "kerneltest-tests.sqlite")
FIXTURES = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures/"))


def _configure_test_db(config):
    """
    Create and configure a test database.

    .. note::
        For some reason, this fails on the in-memory version of SQLite with an error
        about nested transactions.

    Args:
        db_uri (str): The URI to use when creating the database engine. Defaults to an
            in-memory SQLite database.
    Returns:
        sqlalchemy.engine: The database engine.
    """
    db_uri = config["DB_URL"]
    if db_uri.startswith("sqlite:////"):
        # Clean out any old file
        db_path = db_uri.split("sqlite:///")[1]
        if os.path.isfile(db_path):
            os.unlink(db_path)

    global engine
    engine = db.initialize(config)

    if db_uri.startswith("sqlite://"):
        # Necessary to get nested transactions working with SQLite. See:
        # http://docs.sqlalchemy.org/en/latest/dialects/sqlite.html\
        # #serializable-isolation-savepoints-transactional-ddl
        @event.listens_for(engine, "connect")
        def connect_event(dbapi_connection, connection_record):
            """Stop pysqlite from emitting 'BEGIN'."""
            # disable pysqlite's emitting of the BEGIN statement entirely.
            # also stops it from emitting COMMIT before any DDL.
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def begin_event(conn):
            """Emit our own 'BEGIN' instead of letting pysqlite do it."""
            conn.execute("BEGIN")

    @event.listens_for(db.Session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        """Allow tests to call rollback on the session."""
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()

    return engine


class BaseTestCase(unittest.TestCase):
    """
    The base test class.

    This class configures the global scoped session with a test database.
    The test database makes use of nested transactions to provide a clean
    slate for each test. Tests may call both ``commit`` and ``rollback``
    on the database session they acquire from ``kerneltest.db.Session``.
    """

    def setUp(self):
        self.config = copy.deepcopy(default_config.DEFAULTS)
        self.config["OIDC_CLIENT_SECRETS"] = os.path.join(
            FIXTURES, "client_secrets.json"
        )
        self.flask_app = app.create(config=self.config)
        self.flask_client = self.flask_app.test_client()
        # We don't want our SQLAlchemy session thrown away post-request because that rolls
        # back the transaction and no database assertions can be made.
        self.flask_app.teardown_request_funcs = {}

        if engine is None:
            self._engine = _configure_test_db(self.config)
        else:
            self._engine = engine

        self._connection = self._engine.connect()
        db.models.Base.metadata.create_all(bind=self._connection)
        self._transaction = self._connection.begin()

        db.Session.remove()
        db.Session.configure(bind=self._engine, autoflush=False, expire_on_commit=False)
        db.Session().begin_nested()

    def tearDown(self):
        """Roll back all the changes from the test and clean up the session."""
        db.Session().close()
        self._transaction.rollback()
        self._connection.close()
        db.Session.remove()


@contextmanager
def login_user(app, user):
    """
    A context manager to log a user in for testing purposes.

    For example:

        >>> with login_user(self.flask_app, user):
        ...     self.flask_app.test_client().get('/protected/view')

    The above example will cause the request to ``/protected/view`` to occur with the
    provided user being authenticated.

    Args:
        app (flask.Flask): An instance of the Flask application.
        user (kerneltest.app.User): The user to log in.
    """

    def handler(sender, **kwargs):
        g.user = user

    with request_started.connected_to(handler, app):
        yield
