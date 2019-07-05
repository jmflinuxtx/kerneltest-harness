# Licensed under the terms of the GNU GPL License version 2
"""
This module handles the creation and configuration of the Flask application.
"""

import collections
import datetime

from flask_restful import Api
from sqlalchemy.orm.exc import NoResultFound
import flask

from . import default_config, db, __version__, ui_view, authentication, api


User = collections.namedtuple("User", ["groups", "cla", "username"])


def create(config=None):
    """
    Create an instance of the Flask application

    Args:
        config (dict): A dictionary with configuration options to use with the
            application instead of loading the default configuration. Useful for
            testing purposes only.

    Returns:
        flask.Flask: The configured Flask application.
    """
    app = flask.Flask(__name__)
    if config:
        app.config.update(config)
    else:
        app.config.update(default_config.config.load_config())
    db.initialize(app.config)
    authentication.oidc.init_app(app)

    app.api = Api(app)
    app.api.add_resource(api.Results, "/api/v1/results/")
    app.register_blueprint(ui_view.blueprint, url_prefix="/")

    app.before_request(pre_request_user)
    app.teardown_request(post_request_db)
    app.context_processor(include_template_variables)
    app.register_error_handler(NoResultFound, handle_no_result)

    return app


def handle_no_result(exception):
    """Turn SQLAlchemy NotFound into HTTP 404"""
    return "Not found", 404


def include_template_variables():
    """
    A Flask context processor that makes a set of variables available in every
    Jinja2 template.
    """
    releases = db.Release.query.maintained()
    rawhide = db.Release.query.rawhide()
    admin = False
    if flask.g.user:
        admin = ui_view.is_admin()

    return dict(
        date=datetime.datetime.utcnow().strftime("%a %b %d %Y %H:%M"),
        releases=releases,
        rawhide=rawhide,
        version=__version__,
        is_admin=admin,
    )


def post_request_db(*args, **kwargs):
    """Remove the database session after the request is done."""
    db.Session.remove()


def pre_request_user():
    """Set up the user as a flask global object."""
    if ui_view.oidc.user_loggedin:
        flask.g.user = User(
            ui_view.oidc.user_getfield("groups"),
            ui_view.oidc.user_getfield("cla"),
            ui_view.oidc.user_getfield("nickname"),
        )
    else:
        flask.g.user = None
