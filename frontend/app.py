#!/usr/bin/env python
#
# Licensed under the terms of the GNU GPL License version 2

import datetime
import os
import sys
from functools import wraps

import flask
import wtforms as wtf
from flask.ext import wtf as flask_wtf

import dbtools


APP = flask.Flask(__name__)
APP.config.from_object('default_config')
if 'KERNELTEST_CONFIG' in os.environ:  # pragma: no cover
    APP.config.from_envvar('KERNELTEST_CONFIG')

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


@APP.route('/upload/', methods=['GET', 'POST'])
def upload():
    ''' Display the page where new results can be uploaded. '''
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
            return flask.redirect(flask.url_for('upload'))

        relarch = testkver.split(".")
        fver = relarch[-2].replace("fc", "", 1)
        testarch = relarch[-1]

        session = dbtools.dbsetup()
        test = dbtools.KernelTest(
            tester=form.username.data,
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
        'upload.html',
        form=form,
    )

@APP.route('/api/upload/', methods=['POST'])
def api_upload():
    ''' Specific endpoint for some clients to upload their results. '''
    form = ApiUploadForm(csrf_enabled=False)
    httpcode=200
    error = False

    if form.validate_on_submit():
        test_result = form.test_result.data
        api_token = form.api_token.data

        if api_token is None or api_token != APP.config.get('API_KEY', None):
            output = {'error': 'Invalid api_token provided'}
            jsonout = flask.jsonify(output)
            jsonout.status_code = 401
            return jsonout

        logdir = APP.config.get('LOG_DIR', 'logs')
        if not os.path.exists(logdir) and not os.path.isdir(logdir):
            os.mkdir(logdir)

        try:
            (testdate, testset, testkver, testrel,
             testresult, failedtests) = parseresults(test_result)
        except Exception as err:
            output = {'error': 'Invalid input file'}
            jsonout = flask.jsonify(output)
            jsonout.status_code = 400
            return jsonout

        relarch = testkver.split(".")
        fver = relarch[-2].replace("fc", "", 1)
        testarch = relarch[-1]

        session = dbtools.dbsetup()
        test = dbtools.KernelTest(
            tester=form.username.data,
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
            httpcode=200
            output = {'message': 'Upload successful'}
        except:
            SESSION.rollback()
            httpcode=500
            output = {'error': 'Could not save data or result file'}
    else:
        output = {'error': 'Invalid request', 'messages': form.errors}

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout

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
