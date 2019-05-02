import datetime
import logging

from flask_restful import reqparse, Resource, inputs
from fedora_messaging import api as fm_api
from sqlalchemy.orm.exc import NoResultFound
import flask

from . import db
from .authentication import oidc

_log = logging.getLogger(__name__)

_TEST_HELP = (
    'A list of test objects; each object should have a "name" key whose string '
    'value identifies the test, a "passed" key whose boolean value indicates if'
    ' the test passed or not, a "waived" key whose boolean value indicates '
    'whether the test is waived, and a "details" key whose string value contains'
    " details about the test result (logs, links to builds, whatever)"
)
_PAGE_HELP = "The page number of results to retrieve; must be a positive integer"
_ITEMS_PER_PAGE_HELP = (
    "The number of items per page; integer between 1 and {}; it defaults to "
    "{}".format(db.MAX_PAGE_SIZE, db.DEFAULT_PAGE_SIZE)
)

_SCOPES = [
    "openid",
    "https://github.com/jmflinuxtx/kerneltest-harness/oidc/upload_test_run",
]


class Results(Resource):
    def get(self):
        """
        Get a paginated set of test results.
        """
        parser = reqparse.RequestParser(trim=True, bundle_errors=True)
        parser.add_argument(
            "kernel_version",
            type=str,
            help="The kernel version tested. For example: '5.1.3'.",
            location="args",
        )
        parser.add_argument(
            "build_release",
            type=str,
            help="The release of the build tested. For example: '300.fc30'.",
            location="args",
        )
        parser.add_argument(
            "arch",
            type=str,
            help="The architecture the tests were run on. For example: 'aarch64'.",
            location="args",
        )
        parser.add_argument(
            "fedora_version",
            type=int,
            help="The Fedora release the tests were run on. For example: 30.",
            location="args",
        )
        parser.add_argument(
            "page", type=inputs.positive, help=_PAGE_HELP, location="args"
        )
        parser.add_argument(
            "items_per_page",
            type=inputs.int_range(1, db.MAX_PAGE_SIZE),
            help=_ITEMS_PER_PAGE_HELP,
            location="args",
        )
        args = parser.parse_args()

        query = db.TestRun.query
        if args.arch:
            query = query.filter_by(arch=args.arch)
        if args.kernel_version:
            query = query.filter_by(kernel_version=args.kernel_version)
        if args.build_release:
            query = query.filter_by(build_release=args.build_release)
        if args.fedora_version:
            query = query.filter_by(fedora_version=args.fedora_version)
        page_number = args.page or 1
        items_per_page = args.items_per_page or db.DEFAULT_PAGE_SIZE
        page = query.paginate(page=page_number, items_per_page=items_per_page)
        result = {
            "page": page.page,
            "items_per_page": page.items_per_page,
            "total_items": page.total_items,
            "items": [
                {
                    "id": i.id,
                    "created": datetime.datetime.isoformat(i.created),
                    "arch": i.arch,
                    "kernel_version": i.kernel_version,
                    "build_release": i.build_release,
                    "fedora_version": i.fedora_version,
                    "tests": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "passed": t.passed,
                            "waived": t.waived,
                            "details": t.details,
                        }
                        for t in i.tests
                    ],
                }
                for i in page.items
            ],
        }
        return result, 200

    @oidc.accept_token(require_token=True, scopes_required=_SCOPES)
    def post(self):
        parser = reqparse.RequestParser(trim=True, bundle_errors=True)
        parser.add_argument(
            "kernel_version",
            type=str,
            help="The kernel version tested. For example: '5.1.3'.",
            required=True,
            location="json",
        )
        parser.add_argument(
            "build_release",
            type=str,
            help="The release of the build tested. For example: '300.fc30'.",
            required=True,
            location="json",
        )
        parser.add_argument(
            "arch",
            type=str,
            help="The architecture the tests were run on. For example: 'aarch64'.",
            required=True,
            location="json",
        )
        parser.add_argument(
            "fedora_version",
            type=int,
            help="The Fedora release the tests were run on. For example: 30.",
            required=True,
            location="json",
        )
        parser.add_argument(
            "tests", type=list, help=_TEST_HELP, required=True, location="json"
        )
        args = parser.parse_args(strict=True)
        session = db.Session()
        try:
            fedora_version = db.Release.query.filter_by(
                version=args.fedora_version
            ).one()
        except NoResultFound:
            return {"error": "fedora_version was not found"}, 400

        user = flask.g.user.username if flask.g.user else None

        run = db.TestRun(
            kernel_version=args.kernel_version,
            build_release=args.build_release,
            arch=args.arch,
            release=fedora_version,
            user=user,
        )
        for test in args.tests:
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

        # The message format here matches the old fedmsg schema. Eventually it
        # should be changed, but message consumers need to be cataloged and notified.
        message = fm_api.Message(
            topic="kerneltest.upload.new",
            body={
                "agent": user or "anon",
                "test": {
                    "tester": user or "anon",
                    "testdate": str(run.created),
                    "testset": ", ".join([test.name for test in run.tests]),
                    "kernel_version": run.package_name,
                    "fedora_version": run.fedora_version,
                    "arch": run.arch,
                    "release": "Fedora release {}".format(run.fedora_version),
                    "failed_tests": ", ".join(
                        [test.name for test in run.tests if not test.passed]
                    ),
                    "authenticated": True,
                },
            },
        )
        try:
            fm_api.publish(message)
        except (
            fm_api.exceptions.PublishException,
            fm_api.exceptions.ConnectionException,
        ) as err:
            _log.error("Failed to send %r: %r", message, err)

        return {}, 201
