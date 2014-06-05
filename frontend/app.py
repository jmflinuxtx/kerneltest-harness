#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import datetime
import logging
import os
import sys
from functools import wraps

import flask
import wtforms as wtf
from flask.ext.fas_openid import FAS
from flask.ext import wtf as flask_wtf
from sqlalchemy.exc import SQLAlchemyError

import dbtools

__version__ = '1.0'

APP = flask.Flask(__name__)
APP.config.from_object('default_config')
if 'KERNELTEST_CONFIG' in os.environ:  # pragma: no cover
    APP.config.from_envvar('KERNELTEST_CONFIG')

# Set up FAS extension
FAS = FAS(APP)


# Set up the logger
## Send emails for big exception
mail_admin = APP.config.get('MAIL_ADMIN', None)
if mail_admin and not APP.debug:
    MAIL_HANDLER = logging.handlers.SMTPHandler(
        APP.config.get('SMTP_SERVER', '127.0.0.1'),
        'nobody@fedoraproject.org',
        mail_admin,
        'Kerneltest-harness error')
    MAIL_HANDLER.setFormatter(logging.Formatter('''
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        Message:

        %(message)s
    '''))
    MAIL_HANDLER.setLevel(logging.ERROR)
    APP.logger.addHandler(MAIL_HANDLER)


# Log to stderr as well
STDERR_LOG = logging.StreamHandler(sys.stderr)
STDERR_LOG.setLevel(logging.INFO)
APP.logger.addHandler(STDERR_LOG)

SESSION = dbtools.create_session(APP.config['DB_URL'])


## Exception generated when uploading the results into the database.

class InvalidInputException(Exception):
    ''' Exception raised when the user provided an invalid test result file.
    '''
    pass


## Generic functions

def parseresults(log):
    ''' Parse the result of the kernel tests. '''
    for line in log:
        if "Date: " in line:
            testdate = line.replace("Date: ", "", 1).rstrip('\n')
        elif "Test set: " in line:
            testset = line.replace("Test set: ", "", 1).rstrip('\n')
        elif "Kernel: " in line:
            testkver = line.replace("Kernel: ", "", 1).rstrip('\n')
        elif "Release: " in line:
            testrel = line.replace("Release: ", "", 1).rstrip('\n')
        elif "Result: " in line:
            testresult = line.replace("Result: ", "", 1).rstrip('\n')
        elif "Failed Tests: " in line:
            failedtests = line.replace("Failed Tests: ", "", 1).rstrip('\n')
        elif "========" in line:
            break
        #else:
            #APP.logger.info("No match found for: %s", line)
    return testdate, testset, testkver, testrel, testresult, failedtests


def upload_results(test_result, username, authenticated=False):
    ''' Actually try to upload the results into the database.
    '''
    logdir = APP.config.get('LOG_DIR', 'logs')
    if not os.path.exists(logdir) and not os.path.isdir(logdir):
        os.mkdir(logdir)

    try:
        (testdate, testset, testkver, testrel,
         testresult, failedtests) = parseresults(test_result)
    except Exception as err:
        APP.logger.debug(err)
        raise InvalidInputException('Could not parse these results')

    relarch = testkver.split(".")
    fver = relarch[-2].replace("fc", "", 1)
    testarch = relarch[-1]
    # Work around for F19 and older kver conventions
    if testarch == "PAE":
        testarch = "i686+PAE"
        fver = relarch[-3].replace("fc", "", 1)

    test = dbtools.KernelTest(
        tester=username,
        testdate=testdate,
        testset=testset,
        kver=testkver,
        fver=fver,
        testarch=testarch,
        testrel=testrel.decode('utf-8'),
        testresult=testresult,
        failedtests=failedtests,
        authenticated=authenticated,
    )

    SESSION.add(test)
    SESSION.flush()

    filename = '%s.log' % test.testid
    test_result.seek(0)
    test_result.save(os.path.join(logdir, filename))

    return test


## Flask specific utility function

def is_authenticated():
    """ Returns whether the user is currently authenticated or not. """
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None


def is_admin(user):
    """ Is the user an admin. """
    if not user:
        return False

    if not user.cla_done:
        return False

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = [admins]
    admins = set(admins)

    return len(admins.intersection(set(user.groups))) > 0


def fas_login_required(function):
    ''' Flask decorator to ensure that the user is logged in against FAS.
    '''
    @wraps(function)
    def decorated_function(*args, **kwargs):
        ''' Do the actual work of the decorator. '''
        if not hasattr(flask.g, 'fas_user') or flask.g.fas_user is None:
            return flask.redirect(flask.url_for(
                'login', next=flask.request.url))

        return function(*args, **kwargs)
    return decorated_function


@APP.context_processor
def inject_variables():
    ''' Inject some variables in every templates.
    '''
    releases = dbtools.getcurrentreleases(SESSION)
    rawhide = dbtools.getrawhide(SESSION)

    return dict(
        date=datetime.datetime.utcnow().strftime("%a %b %d %Y %H:%M"),
        releases=releases,
        rawhide=rawhide,
        version=__version__,
    )


@APP.teardown_request
def shutdown_session(exception=None):
    ''' Remove the DB session at the end of each request. '''
    SESSION.remove()


## The flask application itself

@APP.route('/')
def index():
    ''' Display the index page. '''
    releases = dbtools.getcurrentreleases(SESSION)
    rawhide = dbtools.getrawhide(SESSION)

    test_matrix = []
    for release in releases:
        arches = dbtools.getarches(SESSION, release.releasenum)
        for arch in arches:
            results = dbtools.getlatest(SESSION, release.releasenum, arch[0])
            test_matrix.append(results)

    return flask.render_template(
        'index.html',
        releases=releases,
        rawhide=rawhide,
        test_matrix=test_matrix,
    )


@APP.route('/release/<release>')
def release(release):
    ''' Display page with information about a specific release. '''
    kernels = dbtools.getkernelsbyrelease(SESSION, release)

    return flask.render_template(
        'release.html',
        release=release,
        kernels=kernels,
    )


@APP.route('/kernel/<kernel>')
def kernel(kernel):
    ''' Display page with information about a specific kernel. '''
    tests = dbtools.getresultsbykernel(SESSION, kernel)

    return flask.render_template(
        'kernel.html',
        kernel=kernel,
        tests=tests,
    )


@APP.route('/logs/<logid>')
def logs(logid):
    ''' Display logs of a specific test run. '''
    logdir = APP.config.get('LOG_DIR', 'logs')
    return flask.send_from_directory(logdir, '%s.log' % logid)


@APP.route('/stats')
def stats():
    ''' Display some stats about the data gathered. '''
    stats = dbtools.get_stats(SESSION)

    return flask.render_template(
        'stats.html',
        stats=stats,
    )


@APP.route('/upload/', methods=['GET', 'POST'])
@fas_login_required
def upload():
    ''' Display the page where new results can be uploaded. '''
    form = UploadForm()
    if form.validate_on_submit():
        test_result = form.test_result.data
        username = flask.g.fas_user.username

        if username == 'kerneltest':
            flask.flash(
                'The `kerneltest` username is reserved, you are not '
                'allowed to use it', 'error')
            return flask.redirect(flask.url_for('upload'))

        try:
            tests = upload_results(
                test_result, username, authenticated=True)
            SESSION.commit()
            flask.flash('Upload successful!')
        except InvalidInputException as err:
            APP.logger.debug(err)
            flask.flash(err.message)
            return flask.redirect(flask.url_for('upload'))
        except SQLAlchemyError as err:
            APP.logger.exception(err)
            flask.flash('Could not save the data in the database')
            SESSION.rollback()
            return flask.redirect(flask.url_for('upload'))
        except OSError as err:
            APP.logger.exception(err)
            SESSION.delete(tests)
            SESSION.commit()
            flask.flash('Could not save the result file')
            return flask.redirect(flask.url_for('upload'))

    return flask.render_template(
        'upload.html',
        form=form,
    )


@APP.route('/upload/autotest', methods=['POST'])
def upload_autotest():
    ''' Specific endpoint for some clients to upload their results. '''
    form = ApiUploadForm(csrf_enabled=False)
    httpcode = 200
    error = False

    if form.validate_on_submit():
        test_result = form.test_result.data
        api_token = form.api_token.data

        if api_token is None or api_token != APP.config.get('API_KEY', None):
            output = {'error': 'Invalid api_token provided'}
            jsonout = flask.jsonify(output)
            jsonout.status_code = 401
            return jsonout

        try:
            tests = upload_results(
                test_result, 'kerneltest', authenticated=True)
            SESSION.commit()
            output = {'message': 'Upload successful!'}
        except InvalidInputException as err:
            APP.logger.debug(err)
            output = {'error': 'Invalid input file'}
            httpcode = 400
        except SQLAlchemyError as err:
            APP.logger.exception(err)
            output = {'error': 'Could not save data in the database'}
            httpcode = 500
        except OSError as err:
            APP.logger.exception(err)
            SESSION.delete(tests)
            SESSION.commit()
            output = {'error': 'Could not save the result file'}
            httpcode = 500
    else:
        httpcode = 400
        output = {'error': 'Invalid request', 'messages': form.errors}

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@APP.route('/upload/anonymous', methods=['POST'])
def upload_anonymous():
    ''' Specific endpoint for some clients to upload their results. '''
    form = UploadForm(csrf_enabled=False)
    httpcode = 200
    error = False

    if form.validate_on_submit():
        test_result = form.test_result.data
        username = form.username.data
        authenticated = False
        if hasattr(flask.g, 'fas_user') and flask.g.fas_user:
            username = flask.g.fas_user.username
            authenticated = True

        if username == 'kerneltest':
            output = {'error': 'The `kerneltest` username is reserved, you '
                'are not allowed to use it'}
            jsonout = flask.jsonify(output)
            jsonout.status_code = 401
            return jsonout

        try:
            tests = upload_results(
                test_result, username, authenticated=authenticated)
            SESSION.commit()
            output = {'message': 'Upload successful!'}
        except InvalidInputException as err:
            APP.logger.debug(err)
            output = {'error': 'Invalid input file'}
            httpcode = 400
        except SQLAlchemyError as err:
            APP.logger.exception(err)
            output = {'error': 'Could not save data in the database'}
            httpcode = 500
        except OSError as err:
            APP.logger.exception(err)
            SESSION.delete(tests)
            SESSION.commit()
            output = {'error': 'Could not save the result file'}
            httpcode = 500
    else:
        httpcode = 400
        output = {'error': 'Invalid request', 'messages': form.errors}

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@APP.route('/login', methods=['GET', 'POST'])
def login():
    ''' Login mechanism for this application.
    '''
    next_url = flask.url_for('index')
    if 'next' in flask.request.args:
        next_url = flask.request.args['next']
    elif 'next' in flask.request.form:
        next_url = flask.request.form['next']

    if next_url == flask.url_for('login'):
        next_url = flask.url_for('index')

    if hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None:
        return flask.redirect(next_url)
    else:
        return FAS.login(return_url=next_url, groups=[])


@APP.route('/logout')
def logout():
    ''' Log out if the user is logged in other do nothing.
    Return to the index page at the end.
    '''
    next_url = flask.url_for('index')
    if 'next' in flask.request.args:
        next_url = flask.request.args['next']
    elif 'next' in flask.request.form:
        next_url = flask.request.form['next']

    if next_url == flask.url_for('login'):
        next_url = flask.url_for('index')
    if hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None:
        FAS.logout()
        flask.flash("You are no longer logged-in")
    return flask.redirect(next_url)


## Form used to upload new results

class UploadForm(flask_wtf.Form):
    ''' Form used to upload the results of kernel tests. '''
    username = wtf.TextField("Username", default='anon')
    test_result = flask_wtf.FileField(
        "Result file", validators=[flask_wtf.file_required()])


class ApiUploadForm(flask_wtf.Form):
    ''' Form used to upload the results of kernel tests via the api. '''
    username = wtf.TextField("Username", default='anon')
    api_token = wtf.TextField(
        "API token", validators=[wtf.validators.Required()])
    test_result = flask_wtf.FileField(
        "Result file", validators=[flask_wtf.file_required()])


if __name__ == '__main__':
    APP.debug = True
    APP.run()
