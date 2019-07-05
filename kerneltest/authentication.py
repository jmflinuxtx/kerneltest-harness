from flask_oidc import OpenIDConnect

#: The OpenID Connect object used for authentication. The application initializes
#: this object in :func:`fedora_notifications.app.create`, but it needs to exist
#: in order for the views to use its decorators.
oidc = OpenIDConnect()
