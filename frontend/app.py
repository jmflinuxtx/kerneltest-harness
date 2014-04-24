#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import datetime
import os
import sys
from functools import wraps

import flask
import wtforms as wtf
from flask.ext.fas_openid import FAS
from flask.ext import wtf as flask_wtf

import dbtools


APP = flask.Flask(__name__)
APP.config.from_object('default_config')
if 'KERNELTEST_CONFIG' in os.environ:  # pragma: no cover
    APP.config.from_envvar('KERNELTEST_CONFIG')

# Set up FAS extension
FAS = FAS(APP)

SESSION = dbtools.create_session(APP.config['DB_URL'])


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
        else:
            print "No match found for: %s" % (line)
    return testdate, testset, testkver, testrel, testresult, failedtests


## Flask specific utility function

def is_admin():
    ''' Return wether the user is recognized as an admin or not. '''
    if not hasattr(flask.g, 'fas_user') or not flask.g.fas_user:
        return False
    else:
        return flask.g.fas_user.username in APP.config.get('ADMINS', [])


def admin_required(function):
    ''' Flask decorator to ensure that the user is logged in against FAS.
    '''
    @wraps(function)
    def decorated_function(*args, **kwargs):
        ''' Do the actual work of the decorator. '''
        if flask.g.fas_user is None:
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
    user_is_admin = is_admin()

    return dict(
        date=datetime.datetime.utcnow().strftime("%a %b %d %Y %H:%M"),
        releases=releases,
        rawhide=rawhide,
        is_admin=user_is_admin,
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


@APP.route('/admin/', methods=['GET', 'POST'])
@admin_required
def admin():
    ''' Display the admin page where new results can be uploaded. '''
    form = UploadForm()
    if form.validate_on_submit():
        test_result = form.test_result.data
        logdir = APP.config.get('LOG_DIR', 'logs')
        if not os.path.exists(logdir) and not os.path.isdir(logdir):
            os.mkdir(logdir)

        try:
            (testdate, testset, testkver, testrel,
             testresult, failedtests) = parseresults(test_result)
        except Exception as err:
            flask.flash('Could not parse these results', 'error')
            return flask.redirect(flask.url_for('admin'))

        relarch = testkver.split(".")
        fver = relarch[-2].replace("fc", "", 1)
        testarch = relarch[-1]

        session = dbtools.dbsetup()
        test = dbtools.KernelTest(
            tester=args.user,
            testdate=testdate,
            testset=testset,
            kver=kver,
            fver=fver,
            testarch=testarch,
            testrel=testrel,
            testresult=testresult,
            failedtests=failedtests
        )
        try:
            SESSION.add(test)
            SESSION.commit()

            filename = '%s.log' % test.testid
            test_result.seek(0)
            test_result.save(os.path.join(logdir, filename))
            flask.flash('Upload successful')
        except:
            SESSION.rollback()
            flask.flash('Upload failed', 'error')

    return flask.render_template(
        'admin.html',
        form=form,
    )


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
    test_result = flask_wtf.FileField(
        "Result file", validators=[flask_wtf.file_required()])


if __name__ == '__main__':
    APP.debug = True
    APP.run()
