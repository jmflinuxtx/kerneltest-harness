# -*- coding: utf-8 -*-
"""This module is responsible for loading the application configuration."""
import logging
import logging.config
import os

import toml


_log = logging.getLogger(__name__)


#: A dictionary of application configuration defaults.
DEFAULTS = dict(
    SECRET_KEY="change me",
    # API key used to authenticate the autotest client, should be private as well
    API_KEY="This is a secret only the cli knows about",
    DB_URL="sqlite:////var/tmp/kernel-test_dev.sqlite",
    SQL_DEBUG=False,
    # FAS group or groups (provided as a list) in which should be the admins
    # of this application
    ADMIN_GROUP=["sysadmin-kernel", "sysadmin-main"],
    # List of MIME types allowed for upload in the application
    ALLOWED_MIMETYPES=["text/plain"],
    # Restrict the size of content uploaded, this is 25Kb
    MAX_CONTENT_LENGTH=1024 * 25,
    OIDC_COOKIE_SECURE=True,
    OIDC_CLIENT_SECRETS="/etc/kerneltest/client_secrets.json",
    OIDC_SCOPES=[
        "openid",
        "profile",
        "https://id.fedoraproject.org/scope/groups",
        "https://id.fedoraproject.org/scope/cla",
        "https://github.com/jmflinuxtx/kerneltest-harness/oidc/upload_test_run",
    ],
    LOG_CONFIG={
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"simple": {"format": "[%(name)s %(levelname)s] %(message)s"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {
            "kerneltest": {"level": "INFO", "propagate": False, "handlers": ["console"]}
        },
        # The root logger configuration; this is a catch-all configuration
        # that applies to all log messages not handled by a different logger
        "root": {"level": "WARNING", "handlers": ["console"]},
    },
)

# Start with a basic logging configuration, which will be replaced by any user-
# specified logging configuration when the configuration is loaded.
logging.config.dictConfig(DEFAULTS["LOG_CONFIG"])


def load():
    """
    Load application configuration from a file and merge it with the default
    configuration.

    If the ``KERNELTEST_CONFIG`` environment variable is set to a filesystem
    path, the configuration will be loaded from that location. Otherwise, the
    path defaults to ``/etc/kerneltest/config.toml``.
    """
    config = DEFAULTS.copy()

    if "KERNELTEST_CONFIG" in os.environ:
        config_path = os.environ["KERNELTEST_CONFIG"]
    else:
        config_path = "/etc/kerneltest/config.toml"

    if os.path.exists(config_path):
        _log.info("Loading configuration from {}".format(config_path))
        with open(config_path) as fd:
            try:
                file_config = toml.load(fd)
                for key in file_config:
                    config[key.upper()] = file_config[key]
            except toml.TomlDecodeError as e:
                msg = "Failed to parse {}: error at line {}, column {}: {}".format(
                    config_path, e.lineno, e.colno, e.msg
                )
                _log.error(msg)
    else:
        _log.info("The configuration file, {}, does not exist.".format(config_path))

    if config["SECRET_KEY"] == DEFAULTS["SECRET_KEY"]:
        _log.warning(
            "SECRET_KEY is not configured, falling back to the default. "
            "This is NOT safe for production deployments!"
        )
    if config["API_KEY"] == DEFAULTS["API_KEY"]:
        _log.warning(
            "API_KEY is not configured, falling back to the default. "
            "This is NOT safe for production deployments!"
        )
    return config


class LazyConfig(dict):
    """This class lazy-loads the configuration file."""

    loaded = False

    def __getitem__(self, *args, **kw):
        if not self.loaded:
            self.load_config()
        return super(LazyConfig, self).__getitem__(*args, **kw)

    def get(self, *args, **kw):
        if not self.loaded:
            self.load_config()
        return super(LazyConfig, self).get(*args, **kw)

    def pop(self, *args, **kw):
        if not self.loaded:
            self.load_config()
        return super(LazyConfig, self).pop(*args, **kw)

    def copy(self, *args, **kw):
        if not self.loaded:
            self.load_config()
        return super(LazyConfig, self).copy(*args, **kw)

    def update(self, *args, **kw):
        if not self.loaded:
            self.load_config()
        return super(LazyConfig, self).update(*args, **kw)

    def load_config(self):
        self.loaded = True
        self.update(load())
        logging.config.dictConfig(self["LOG_CONFIG"])
        return self


#: The application configuration dictionary.
config = LazyConfig()
