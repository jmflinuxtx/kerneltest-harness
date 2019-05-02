"""Unit tests for :mod:`kerneltest.ui_view`"""

from kerneltest.db import Session, Release, TestRun, Test
from kerneltest.tests.base import BaseTestCase


class IndexTests(BaseTestCase):
    """Tests for :func:`kerneltest.ui_view.index`"""

    def test_get(self):
        """Assert retrieving the home page results in HTTP 200"""
        result = self.flask_client.get("/")
        assert result.status_code == 200

    def test_get_with_releases(self):
        session = Session()
        session.add(Release(version=31, support="RAWHIDE"))
        session.add(Release(version=30, support="RELEASE"))
        session.add(Release(version=29, support="RETIRED"))
        session.commit()

        result = self.flask_client.get("/")

        assert result.status_code == 200
        assert "Fedora Rawhide" in result.get_data(as_text=True)
        assert "Fedora 30" in result.get_data(as_text=True)
        assert "Fedora 29" not in result.get_data(as_text=True)

    def test_get_with_tests(self):
        session = Session()
        release = Release(version=31, support="RAWHIDE")
        run = TestRun(
            kernel_version="5.1.2",
            build_release="300.fc30",
            arch="ppc64le",
            release=release,
            user="kerneltest",
        )
        test = Test(
            name="Secure Boot",
            passed=True,
            waived=False,
            details="Signature valid",
            run=run,
        )
        session.add_all([release, run, test])
        session.commit()

        result = self.flask_client.get("/")

        assert result.status_code == 200
        assert "5.1.2-300.fc30.ppc64le" in result.get_data(as_text=True)
        assert "PASS" in result.get_data(as_text=True)


class ReleaseTests(BaseTestCase):
    def test_get(self):
        """Assert releases can be retrieved"""
        session = Session()
        session.add(Release(version=31, support="RAWHIDE"))
        session.commit()

        result = self.flask_client.get("/release/31")

        assert result.status_code == 200

    def test_get_404(self):
        """Assert a 404 status is returned for non-existing releases"""
        result = self.flask_client.get("/release/31")

        assert result.status_code == 404

    def test_get_tests_paged(self):
        session = Session()
        release = Release(version=31, support="RELEASE")
        session.add(release)
        for r in range(26):
            run = TestRun(
                kernel_version="5.{}.0".format(r),
                build_release="300.fc30",
                arch="ppc64le",
                release=release,
                user="kerneltest",
            )
            test = Test(
                name="Secure Boot",
                passed=True,
                waived=False,
                details="Signature valid",
                run=run,
            )
            session.add_all([run, test])
        session.commit()

        result = self.flask_client.get("/release/31")
        assert result.status_code == 200
        for r in range(1, 26):
            assert "5.{}.0".format(r) in result.get_data(as_text=True)
        assert "5.0.0" not in result.get_data(as_text=True)

        result = self.flask_client.get("/release/31?page=2")
        assert "5.0.0" in result.get_data(as_text=True)


class KernelTests(BaseTestCase):
    """Tests for the /kernel/<kernel> endpoint."""

    def test_get(self):
        """Assert getting tests for a kernel works."""
        session = Session()
        release = Release(version=31, support="RELEASE")
        run = TestRun(
            kernel_version="5.1.0",
            build_release="300.fc30",
            arch="ppc64le",
            release=release,
            user="jcline",
        )
        test = Test(
            name="Secure Boot",
            passed=True,
            waived=False,
            details="Signature valid",
            run=run,
        )
        session.add_all([release, run, test])
        session.commit()

        result = self.flask_client.get("/kernel/5.1.0")
        assert result.status_code == 200

    def test_get_404(self):
        """Assert a 404 status is returned for non-existing kernels"""
        result = self.flask_client.get("/kernel/clearly-not-a-kernel-version")

        assert result.status_code == 404

    def test_get_tests_paged(self):
        """Assert only 25 tests per page are returned."""
        session = Session()
        release = Release(version=31, support="RELEASE")
        session.add(release)
        for r in range(26):
            run = TestRun(
                kernel_version="5.1.0",
                build_release="300.fc30",
                arch="ppc64le",
                release=release,
                user=str(r),
            )
            test = Test(
                name="Secure Boot",
                passed=True,
                waived=False,
                details="Signature valid",
                run=run,
            )
            session.add_all([run, test])
        session.commit()

        result = self.flask_client.get("/kernel/5.1.0")

        assert result.status_code == 200
        tests = [
            w
            for w in result.get_data(as_text=True).split()
            if w.strip() == "<td>5.1.0</td>"
        ]
        assert len(tests) == 25

        result = self.flask_client.get("/kernel/5.1.0?page=2")
        tests = [
            w
            for w in result.get_data(as_text=True).split()
            if w.strip() == "<td>5.1.0</td>"
        ]
        assert len(tests) == 1


class ResultsTests(BaseTestCase):
    """Tests for the /results/<test_run_id> endpoint."""

    def test_get_404(self):
        """Assert the server returns a 404 if the result doesn't exist."""
        result = self.flask_client.get("/results/fourohfour")

        assert result.status_code == 404

    def test_get_passed(self):
        """Assert passing test results are shown properly."""
        session = Session()
        release = Release(version=31, support="RELEASE")
        run = TestRun(
            kernel_version="5.1.0",
            build_release="300.fc30",
            arch="ppc64le",
            release=release,
            user="jcline",
        )
        test = Test(
            name="Secure Boot",
            passed=True,
            waived=False,
            details="Signature valid",
            run=run,
        )
        session.add_all([release, run, test])
        session.commit()

        result = self.flask_client.get("/results/1")

        assert result.status_code == 200
        assert "✅ Passed" in result.get_data(as_text=True)

    def test_get_failed(self):
        """Assert passing test results are shown properly."""
        session = Session()
        release = Release(version=31, support="RELEASE")
        run = TestRun(
            kernel_version="5.1.0",
            build_release="300.fc30",
            arch="ppc64le",
            release=release,
            user="jcline",
        )
        test = Test(
            name="Secure Boot",
            passed=False,
            waived=True,
            details="Signature valid",
            run=run,
        )
        session.add_all([release, run, test])
        session.commit()

        result = self.flask_client.get("/results/1")

        assert result.status_code == 200
        assert "🚧❌ Failed (waived)" in result.get_data(as_text=True)

    def test_get_passed_and_waived(self):
        """Assert passed waived tests are noted."""
        session = Session()
        release = Release(version=31, support="RELEASE")
        run = TestRun(
            kernel_version="5.1.0",
            build_release="300.fc30",
            arch="ppc64le",
            release=release,
            user="jcline",
        )
        test = Test(
            name="Secure Boot",
            passed=True,
            waived=True,
            details="Signature valid",
            run=run,
        )
        session.add_all([release, run, test])
        session.commit()

        result = self.flask_client.get("/results/1")

        assert result.status_code == 200
        assert "🚧✅ Passed (waived)" in result.get_data(as_text=True)

    def test_get_failed_and_waived(self):
        """Assert failed waived tests are noted."""
        session = Session()
        release = Release(version=31, support="RELEASE")
        run = TestRun(
            kernel_version="5.1.0",
            build_release="300.fc30",
            arch="ppc64le",
            release=release,
            user="jcline",
        )
        test = Test(
            name="Secure Boot",
            passed=False,
            waived=True,
            details="Signature valid",
            run=run,
        )
        session.add_all([release, run, test])
        session.commit()

        result = self.flask_client.get("/results/1")

        assert result.status_code == 200
        assert "❌ Failed" in result.get_data(as_text=True)


class StatsTest(BaseTestCase):
    """Tests for the /stats endpoint."""

    def test_get(self):
        """Assert retrieving stats with a populated database works."""
        session = Session()
        for v in range(5):
            release = Release(version=v, support="RAWHIDE")
            session.add(release)
            for k in range(10):
                for u in range(100):
                    run = TestRun(
                        kernel_version="{}.{}.0".format(v, k),
                        build_release="300.fc30",
                        arch="aarch64",
                        release=release,
                        user=str(u),
                    )
                    test1 = Test(
                        name="Secure Boot",
                        passed=True,
                        waived=False,
                        details="Signature valid",
                        run=run,
                    )
                    test2 = Test(
                        name="Boot Test",
                        passed=True,
                        waived=False,
                        details="Much boot",
                        run=run,
                    )
                    session.add_all([run, test1, test2])
        session.commit()

        result = self.flask_client.get("/stats")
        assert result.status_code == 200
        assert "<th>Number of tests</th>\n    <td>5000</td>" in result.get_data(
            as_text=True
        )
        assert "<th>Number of kernels tested</th>\n    <td>50</td>" in result.get_data(
            as_text=True
        )
        assert "<th>Number of arches tested</th>\n    <td>1</td>" in result.get_data(
            as_text=True
        )

    def test_get_nothing(self):
        result = self.flask_client.get("/stats")
        assert result.status_code == 200
