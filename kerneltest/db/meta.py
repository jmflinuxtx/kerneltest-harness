"""
This module sets up the basic database objects that all other database modules
will rely on. This includes the declarative base class and global scoped
session.

This is in its own module to avoid circular imports from forming. Models and
events need to be imported by ``__init__.py``, but they also need access to
the :class:`Base` model and :class:`Session`.
"""
import collections

from sqlalchemy import create_engine, event
from sqlalchemy.ext import declarative
from sqlalchemy.orm import sessionmaker, scoped_session, query as sa_query


#: This is a configured scoped session. It creates thread-local sessions. This
#: means that ``Session() is Session()`` is ``True``. This is a convenient way
#: to avoid passing a session instance around. Consult SQLAlchemy's documentation
#: for details.
#:
#: Before you can use this, you must call :func:`initialize`.
Session = scoped_session(sessionmaker())

#: A namedtuple that represents a page of database results.
Page = collections.namedtuple(
    "Page", ("items", "page", "items_per_page", "total_items")
)

#: The default number of items in a page when using pagination.
DEFAULT_PAGE_SIZE = 25

#: The maximum page size when using pagination.
MAX_PAGE_SIZE = 250


def initialize(config):
    """
    Initialize the database.

    This creates a database engine from the provided configuration and
    configures the scoped session to use the engine.

    .. note::
        This approach makes it very simple to write your unit tests. Since
        everything accessing the database should use the :data:`Session`,
        just call this function with your test database configuration in your
        test setup code.

    Args:
        config (dict): A dictionary that contains the configuration necessary
            to initialize the database.

    Returns:
        sqlalchemy.engine: The database engine created from the configuration.
    """
    engine = create_engine(config["DB_URL"], echo=config["SQL_DEBUG"])
    if config["DB_URL"].startswith("sqlite:"):
        # Flip on foreign key constraints if the database in use is SQLite. See
        # http://docs.sqlalchemy.org/en/latest/dialects/sqlite.html#foreign-key-support
        event.listen(
            engine,
            "connect",
            lambda db_con, con_record: db_con.execute("PRAGMA foreign_keys=ON"),
        )
    Session.configure(bind=engine)
    return engine


class BaseQuery(sa_query.Query):
    """A base Query object that provides queries for all models."""

    def paginate(self, page=1, items_per_page=DEFAULT_PAGE_SIZE):
        """
        Retrieve a page of items.

        Args:
            page (int): The page number to retrieve. This page is 1-indexed and
                defaults to 1. This value should be validated before being passed
                to this function.
            items_per_page (int): The number of items per page. This defaults
                to 25. This value should be validated before being passed
                to this function.

        Returns:
            Page: A namedtuple of the items.
        """
        total_items = self.count()
        items = self.limit(items_per_page).offset(items_per_page * (page - 1)).all()
        return Page(
            items=items,
            page=page,
            total_items=total_items,
            items_per_page=items_per_page,
        )


class DeclarativeBaseMixin(object):
    """
    A mix-in class for the declarative base class.

    This provides a place to attach functionality that should be available on
    all models derived from the declarative base.

    Attributes:
        query (sqlalchemy.orm.query.Query): a class property which produces a
            :class:`BaseQuery` object against the class and the current Session
            when called. Classes that want a customized Query class should
            sub-class :class:`BaseQuery` and explicitly set the query property
            on the model.
    """

    query = Session.query_property(query_cls=BaseQuery)


#: The SQLAlchemy declarative base class all models must sub-class.
Base = declarative.declarative_base(cls=DeclarativeBaseMixin)
