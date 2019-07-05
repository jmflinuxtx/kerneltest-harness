import logging
import json

from fedora_messaging import api as fm_api
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
import flask

from . import default_config, db, forms
from .authentication import oidc

#: The Flask Blueprint for the web user interface
blueprint = flask.Blueprint(
    "ui", __name__, static_folder="static", template_folder="templates"
)

_log = logging.getLogger(__name__)


@blueprint.route("/")
def index():
    """ Display the index page. """
    releases = db.Release.query.maintained()
    rawhide = db.Release.query.rawhide()

    test_matrix = []
    for release in releases:
        arches = [
            t.arch
            for t in db.TestRun.query.filter_by(release=release)
            .distinct(db.TestRun.arch)
            .all()
        ]
        for arch in arches:
            results = (
                db.TestRun.query.filter_by(
                    user="kerneltest", release=release, arch=arch
                )
                .order_by(db.TestRun.id.desc())
                .first()
            )
            if results:
                test_matrix.append(results)

    return flask.render_template(
        "index.html", releases=releases, rawhide=rawhide, test_matrix=test_matrix
    )


@blueprint.route("/login/")
@oidc.require_login
def login():
    """Log in using OpenID Connect."""
    flask.flash("You successfully logged in, {}".format(flask.g.user.username))
    return flask.redirect(flask.url_for("ui.index"))


@blueprint.route("/logout/")
def logout():
    """Log out."""
    oidc.logout()
    flask.flash("You successfully logged out!")
    return flask.redirect(flask.url_for("ui.index"))


@blueprint.route("/release/<release>")
def release(release):
    """ Display page with information about a specific release. """
    page = int(flask.request.args.get("page", 1))
    release = db.Release.query.filter_by(version=release).one()
    tests = (
        db.TestRun.query.distinct(db.TestRun.kernel_version)
        .filter_by(release=release)
        .order_by(db.TestRun.kernel_version.desc())
        .paginate(page=page)
    )

    return flask.render_template("release.html", release=release, page=tests)


@blueprint.route("/kernel/<kernel>")
def kernel(kernel):
    """ Display page with information about a specific kernel. """
    page = int(flask.request.args.get("page", 1))
    tests = (
        db.TestRun.query.filter_by(kernel_version=kernel)
        .order_by(db.TestRun.id.desc())
        .paginate(page=page)
    )
    if tests.total_items == 0:
        return "Not found", 404

    return flask.render_template("kernel.html", kernel=kernel, page=tests)


@blueprint.route("/results/<int:test_run_id>")
def results(test_run_id):
    """
    Shows an individual test run.
    """
    test_run = db.TestRun.query.filter_by(id=test_run_id).one()
    return flask.render_template("results.html", test_run=test_run)


@blueprint.route("/stats")
def stats():
    """ Display some stats about the data gathered. """
    stats = db.models.get_stats()

    return flask.render_template("stats.html", stats=stats)


@blueprint.route("/upload/", methods=["GET", "POST"])
@oidc.require_login
def upload():
    """ Display the page where new results can be uploaded. """
    form = forms.UploadForm()
    if form.validate_on_submit():
        test_result = form.test_result.data
        username = flask.g.user.username

        if username == "kerneltest":
            flask.flash(
                "The `kerneltest` username is reserved, you are not "
                "allowed to use it",
                "error",
            )
            return flask.redirect(flask.url_for("ui.upload"))

        try:
            session = db.Session()
            results = json.load(test_result.stream)

            try:
                fedora_version = db.Release.query.filter_by(
                    version=results["fedora_version"]
                ).one()
            except NoResultFound:
                return {"error": "fedora_version was not found"}, 400

            run = db.TestRun(
                kernel_version=results["kernel_version"],
                build_release=results["build_release"],
                arch=results["arch"],
                release=fedora_version,
                user=username,
            )
            for test in results["tests"]:
                session.add(
                    db.Test(
                        name=test["name"],
                        passed=test["passed"],
                        waived=test["waived"],
                        details=test["details"],
                        run=run,
                    )
                )
            session.add(run)
            session.commit()
            flask.flash("Upload successful!")
        except ValueError:
            flask.flash("Invalid JSON document!")
            return flask.redirect(flask.url_for("ui.upload"))
        except SQLAlchemyError as err:
            _log.exception(err)
            flask.flash("Could not save the data in the database")
            db.Session.rollback()
            return flask.redirect(flask.url_for("ui.upload"))

    return flask.render_template("upload.html", form=form)


def is_admin():
    return (
        len(
            set(default_config.config["ADMIN_GROUP"]).intersection(
                set(flask.g.user.groups)
            )
        )
        > 0
    )


@blueprint.route("/admin/new", methods=("GET", "POST"))
@oidc.require_login
def admin_new_release():
    if not is_admin():
        flask.flash("You are not an admin", "error")
        return flask.redirect(flask.url_for("ui.index"))

    form = forms.ReleaseForm()
    if form.validate_on_submit():
        release = db.Release()
        form.populate_obj(obj=release)
        db.Session.add(release)
        db.Session.commit()

        message = fm_api.Message(
            topic="kerneltest.release.new",
            body={
                "agent": flask.g.user.username,
                "release": {"releasenum": release.version, "support": release.support},
            },
        )
        try:
            fm_api.publish(message)
        except (
            fm_api.exceptions.ConnectionException,
            fm_api.exceptions.ConnectionException,
        ):
            pass

        flask.flash('Release "%s" added' % release.version)
        return flask.redirect(flask.url_for("ui.index"))
    return flask.render_template(
        "release_new.html", form=form, submit_text="Create release"
    )


@blueprint.route("/admin/<relnum>/edit", methods=("GET", "POST"))
@oidc.require_login
def admin_edit_release(relnum):
    if not is_admin():
        flask.flash("You are not an admin", "error")
        return flask.redirect(flask.url_for("ui.index"))

    release = db.Release.query.filter_by(version=relnum).one_or_none()
    if not release:
        flask.flash("No release %s found" % relnum)
        return flask.redirect(flask.url_for("ui.index"))

    form = forms.ReleaseForm(obj=release)
    if form.validate_on_submit():
        form.populate_obj(obj=release)
        db.Session.commit()

        message = fm_api.Message(
            topic="kerneltest.release.edit",
            body={
                "agent": flask.g.user.username,
                "release": {"releasenum": release.version, "support": release.support},
            },
        )
        try:
            fm_api.publish(message)
        except (
            fm_api.exceptions.ConnectionException,
            fm_api.exceptions.ConnectionException,
        ):
            pass

        flask.flash('Release "%s" updated' % release.version)
        return flask.redirect(flask.url_for("ui.index"))
    return flask.render_template(
        "release_new.html", form=form, release=release, submit_text="Edit release"
    )
