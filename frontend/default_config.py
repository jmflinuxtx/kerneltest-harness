# -*- coding: utf-8 -*-


# Secret key used to generate the CRSF token, thus very private!
SECRET_KEY = '<change me before using me in prod>'

# URL used to connect to the database
DB_URL = 'sqlite:////var/tmp/kernel-test_dev.sqlite'

# Specify where the logs of the tests should be stored
LOG_DIR = 'logs'

# API key used to authenticate the autotest client, should be private as well
API_KEY = 'This is a secret only the cli knows about'

# Email of the admin that should receive the error emails
MAIL_ADMIN = None

# FAS group or groups (provided as a list) in which should be the admins
# of this application
ADMIN_GROUP = ['sysadmin-kernel', 'sysadmin-main']

# List of MIME types allowed for upload in the application
ALLOWED_MIMETYPES = ['text/plain']

# Restrict the size of content uploaded, this is 10Kb
MAX_CONTENT_LENGTH = 1024 * 10
