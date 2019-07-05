from unittest import mock

import flask

from kerneltest.tests import base


class WsgiAppTests(base.BaseTestCase):
    """Tests for kerneltest.wsgi."""

    def test_wsgi_app(self):
        """Assert the WSGI application is created."""
        # Import triggers creation, so import here to set up the test configuration
        with mock.patch("kerneltest.default_config.config") as mock_conf:
            mock_conf.load_config.return_value = self.config
            from kerneltest import wsgi
        assert isinstance(wsgi.application, flask.Flask)
