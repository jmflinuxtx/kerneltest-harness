from unittest import mock
import datetime
import json

from flask import request_started, g
from fedora_messaging.testing import mock_sends
from fedora_messaging import api as fm_api, exceptions as fm_exceptions

from .. import db, authentication, api
from ..app import User
from .base import BaseTestCase


class ResultsGetTests(BaseTestCase):
    """Tests for the GET verb on the /api/v1/results/ endpoint."""

    def test_empty(self):
        """Assert unathenticated requests return 401."""
        result = self.flask_client.get("/api/v1/results/")

        assert result.status_code == 200
        assert json.loads(result.get_data(as_text=True)) == {
            "page": 1,
            "items_per_page": 25,
            "total_items": 0,
            "items": [],
        }

    def test_get_bad_page(self):
        """Assert retrieving an invalid page results in a HTTP 400."""
        result = self.flask_client.get("/api/v1/results/?page=0")

        assert result.status_code == 400
        assert json.loads(result.get_data(as_text=True)) == {
            "message": {"page": api._PAGE_HELP}
        }

    def test_get_bad_items_per_page(self):
        """Assert retrieving an invalid page results in a HTTP 400."""
        result = self.flask_client.get("/api/v1/results/?items_per_page=0")

        assert result.status_code == 400
        assert json.loads(result.get_data(as_text=True)) == {
            "message": {"items_per_page": api._ITEMS_PER_PAGE_HELP}
        }

    def test_get_too_many_items_per_page(self):
        """Assert retrieving an invalid page results in a HTTP 400."""
        result = self.flask_client.get("/api/v1/results/?items_per_page=1000")

        assert result.status_code == 400
        assert json.loads(result.get_data(as_text=True)) == {
            "message": {"items_per_page": api._ITEMS_PER_PAGE_HELP}
        }

    def test_get(self):
        """Assert a plain GET returns the results."""
        session = db.Session()
        release = db.Release(version="31", support="RAWHIDE")
        created = datetime.datetime.utcnow()
        run = db.TestRun(
            kernel_version="5.1.0",
            arch="aarch64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        test = db.Test(
            name="Insanity Test", passed=False, waived=False, details="Aaaaah!", run=run
        )
        session.add_all([release, run, test])
        session.commit()
        expected = {
            "page": 1,
            "items_per_page": 25,
            "total_items": 1,
            "items": [
                {
                    "id": 1,
                    "created": created.isoformat(),
                    "arch": "aarch64",
                    "kernel_version": "5.1.0",
                    "build_release": "300.fc30",
                    "fedora_version": 31,
                    "tests": [
                        {
                            "id": 1,
                            "name": "Insanity Test",
                            "passed": False,
                            "waived": False,
                            "details": "Aaaaah!",
                        }
                    ],
                }
            ],
        }

        result = self.flask_client.get("/api/v1/results/")

        assert result.status_code == 200
        assert json.loads(result.get_data(as_text=True)) == expected

    def test_get_paging(self):
        """Assert a paging arguments for GET work."""
        session = db.Session()
        release = db.Release(version="31", support="RAWHIDE")
        created = datetime.datetime.utcnow()
        run1 = db.TestRun(
            kernel_version="5.1.0",
            arch="aarch64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        run2 = db.TestRun(
            kernel_version="5.1.1",
            arch="aarch64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        session.add_all([release, run1, run2])
        session.commit()
        req1_expected = {
            "page": 1,
            "items_per_page": 1,
            "total_items": 2,
            "items": [
                {
                    "id": 1,
                    "created": created.isoformat(),
                    "arch": "aarch64",
                    "kernel_version": "5.1.0",
                    "build_release": "300.fc30",
                    "fedora_version": 31,
                    "tests": [],
                }
            ],
        }
        req2_expected = {
            "page": 2,
            "items_per_page": 1,
            "total_items": 2,
            "items": [
                {
                    "id": 2,
                    "created": created.isoformat(),
                    "arch": "aarch64",
                    "kernel_version": "5.1.1",
                    "build_release": "300.fc30",
                    "fedora_version": 31,
                    "tests": [],
                }
            ],
        }

        req1 = self.flask_client.get("/api/v1/results/?items_per_page=1")
        req2 = self.flask_client.get("/api/v1/results/?items_per_page=1&page=2")

        assert req1.status_code == 200
        assert req2.status_code == 200
        assert json.loads(req1.get_data(as_text=True)) == req1_expected
        assert json.loads(req2.get_data(as_text=True)) == req2_expected

    def test_get_filter_arch(self):
        """Assert queries can be filtered by architecture"""
        session = db.Session()
        release = db.Release(version="31", support="RAWHIDE")
        created = datetime.datetime.utcnow()
        run1 = db.TestRun(
            kernel_version="5.1.0",
            arch="aarch64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        run2 = db.TestRun(
            kernel_version="5.1.0",
            arch="x86_64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        session.add_all([release, run1, run2])
        session.commit()

        result = self.flask_client.get("/api/v1/results/?arch=aarch64")

        assert result.status_code == 200
        result = json.loads(result.get_data(as_text=True))
        assert result["total_items"] == 1
        assert result["items"] == [
            {
                "id": 1,
                "created": created.isoformat(),
                "arch": "aarch64",
                "kernel_version": "5.1.0",
                "build_release": "300.fc30",
                "fedora_version": 31,
                "tests": [],
            }
        ]

    def test_get_filter_kernel_version(self):
        """Assert queries can be filtered by kernel versions."""
        session = db.Session()
        release = db.Release(version="31", support="RAWHIDE")
        created = datetime.datetime.utcnow()
        run1 = db.TestRun(
            kernel_version="5.1.1",
            arch="aarch64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        run2 = db.TestRun(
            kernel_version="5.1.0",
            arch="x86_64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        session.add_all([release, run1, run2])
        session.commit()

        result = self.flask_client.get("/api/v1/results/?kernel_version=5.1.1")

        assert result.status_code == 200
        result = json.loads(result.get_data(as_text=True))
        assert result["total_items"] == 1
        assert result["items"] == [
            {
                "id": 1,
                "created": created.isoformat(),
                "arch": "aarch64",
                "kernel_version": "5.1.1",
                "build_release": "300.fc30",
                "fedora_version": 31,
                "tests": [],
            }
        ]

    def test_get_filter_build_release(self):
        """Assert queries can be filtered by build release"""
        session = db.Session()
        release = db.Release(version="31", support="RAWHIDE")
        created = datetime.datetime.utcnow()
        run1 = db.TestRun(
            kernel_version="5.1.0",
            arch="aarch64",
            build_release="300.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        run2 = db.TestRun(
            kernel_version="5.1.0",
            arch="x86_64",
            build_release="301.fc30",
            release=release,
            user="kerneltest",
            created=created,
        )
        session.add_all([release, run1, run2])
        session.commit()

        result = self.flask_client.get("/api/v1/results/?build_release=300.fc30")

        assert result.status_code == 200
        result = json.loads(result.get_data(as_text=True))
        assert result["total_items"] == 1
        assert result["items"] == [
            {
                "id": 1,
                "created": created.isoformat(),
                "arch": "aarch64",
                "kernel_version": "5.1.0",
                "build_release": "300.fc30",
                "fedora_version": 31,
                "tests": [],
            }
        ]

    def test_get_filter_fedora_version(self):
        """Assert queries can be filtered by Fedora version"""
        session = db.Session()
        rawhide = db.Release(version="31", support="RAWHIDE")
        stable = db.Release(version="30", support="RELEASE")
        created = datetime.datetime.utcnow()
        run1 = db.TestRun(
            kernel_version="5.2.0",
            arch="aarch64",
            build_release="0.rc0.git9.1.fc31",
            release=rawhide,
            user="kerneltest",
            created=created,
        )
        run2 = db.TestRun(
            kernel_version="5.1.3",
            arch="x86_64",
            build_release="300.fc30",
            release=stable,
            user="kerneltest",
            created=created,
        )
        session.add_all([rawhide, stable, run1, run2])
        session.commit()

        result = self.flask_client.get("/api/v1/results/?fedora_version=30")

        assert result.status_code == 200
        result = json.loads(result.get_data(as_text=True))
        assert result["total_items"] == 1
        assert result["items"] == [
            {
                "id": 2,
                "created": created.isoformat(),
                "arch": "x86_64",
                "kernel_version": "5.1.3",
                "build_release": "300.fc30",
                "fedora_version": 30,
                "tests": [],
            }
        ]


class ResultsPostTests(BaseTestCase):
    def test_create_unauthenticated(self):
        """Assert unathenticated requests create anonymous results."""
        test_run = {
            "kernel_version": "5.1.2",
            "build_release": "300.fc30",
            "arch": "aarch64",
            "fedora_version": 29,
            "tests": [
                {
                    "name": "Boot test",
                    "passed": True,
                    "waived": False,
                    "details": "Something something booted successfully",
                }
            ],
        }
        db.Session.add(db.Release(version=29))
        db.Session.commit()

        with mock_sends(fm_api.Message):
            result = self.flask_client.post("/api/v1/results/", json=test_run)
        assert result.status_code == 201
        assert db.TestRun.query.count() == 1
        assert db.TestRun.query.one().user is None
        assert db.Test.query.count() == 1

    def test_create_no_release(self):
        """Assert test results can be created."""
        test_run = {
            "kernel_version": "5.1.2",
            "build_release": "300.fc30",
            "arch": "aarch64",
            "fedora_version": 29,
            "tests": [
                {
                    "name": "Boot test",
                    "passed": True,
                    "waived": False,
                    "details": "Something something booted successfully",
                }
            ],
        }

        with mock.patch.object(
            authentication.oidc, "validate_token", return_value=True
        ):
            result = self.flask_client.post("/api/v1/results/", json=test_run)
        assert result.status_code == 400

    def test_create(self):
        """Assert test results can be created."""
        test_run = {
            "kernel_version": "5.1.2",
            "build_release": "300.fc30",
            "arch": "aarch64",
            "fedora_version": 29,
            "tests": [
                {
                    "name": "Boot test",
                    "passed": True,
                    "waived": False,
                    "details": "Something something booted successfully",
                }
            ],
        }
        db.Session.add(db.Release(version=29))
        db.Session.commit()

        with mock.patch.object(
            authentication.oidc, "validate_token", return_value=True
        ):

            def handler(sender, **kwargs):
                g.user = User(None, None, "jcline")

            with request_started.connected_to(handler, self.flask_app):
                with mock_sends(fm_api.Message):
                    result = self.flask_client.post("/api/v1/results/", json=test_run)
        assert result.status_code == 201
        assert db.TestRun.query.count() == 1
        assert db.Test.query.count() == 1

    @mock.patch("kerneltest.api.fm_api.publish")
    def test_create_failed_message(self, mock_publish):
        """Assert test results can be created."""
        test_run = {
            "kernel_version": "5.1.2",
            "build_release": "300.fc30",
            "arch": "aarch64",
            "fedora_version": 29,
            "tests": [
                {
                    "name": "Boot test",
                    "passed": True,
                    "waived": False,
                    "details": "Something something booted successfully",
                }
            ],
        }
        db.Session.add(db.Release(version=29))
        db.Session.commit()
        mock_publish.side_effect = fm_exceptions.PublishException()

        with mock.patch.object(
            authentication.oidc, "validate_token", return_value=True
        ):

            def handler(sender, **kwargs):
                g.user = User(None, None, "jcline")

            with request_started.connected_to(handler, self.flask_app):
                result = self.flask_client.post("/api/v1/results/", json=test_run)
        assert result.status_code == 201
        assert db.TestRun.query.count() == 1
        assert db.Test.query.count() == 1
