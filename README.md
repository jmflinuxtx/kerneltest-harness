==================
kerneltest-harness
==================

Fedora automated kernel test harness


Development Setup
=================


Authentication
--------------

User authentication is provided by OpenID Connect (OIDC). To authenticate against
the development deployment of Fedora's identity provider, run:

```
$ oidc-register --output-file=client_secrets.json \
  https://iddev.fedorainfracloud.org/ http://localhost:5000
```

Note: The redirect URL you use (http://localhost:5000 in this case) MUST match
the URL you visit in the browser.

You will also need to provide a configuration file, written in TOML,
with at least the following settings:
```
OIDC_CLIENT_SECRETS = "/path/to/client_secrets.json"
OIDC_COOKIE_SECURE = false  # This is only safe because we're redirecting to localhost.
```

Save the above to ``config.toml``. Finally, run the application with:

```
FLASK_APP=kerneltest.wsgi FLASK_DEBUG=1 KERNELTEST_CONFIG=config.toml flask run
```
