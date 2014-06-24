# Licensed under the terms of the GNU GPL License version 2

'''
kerneltest tests.
'''

__requires__ = ['SQLAlchemy >= 0.7']
import pkg_resources

import json
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import kerneltest.app as app
import kerneltest.dbtools as dbtools
from tests import Modeltests, user_set, FakeFasUser


class KerneltestTests(Modeltests):
    """ kerneltest tests. """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(KerneltestTests, self).setUp()

        app.APP.config['TESTING'] = True
        app.SESSION = self.session
        self.app = app.APP.test_client()

    def test_upload_results_loggedin(self):
        ''' Test the app.upload_results function. '''
        folder = os.path.dirname(os.path.abspath(__file__))
        filename = '1.log'
        full_path = os.path.join(folder, filename)

        user = FakeFasUser()
        with user_set(app.APP, user):
            output = self.app.get('/upload/')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<td><input id="test_result" name="test_result" '
                'type="file"></td>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            # Valid upload via the UI
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/upload/', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="message">Upload successful!</li>' in output.data)

            # Valid upload authenticated and via the anonymous API
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
            }
            output = self.app.post('/upload/anonymous', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(data, {'message': 'Upload successful!'})

            # Invalid file upload
            full_path = os.path.join(folder, 'invalid.log')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/upload/', data=data)
            self.assertEqual(output.status_code, 302)

            # Invalid file upload
            full_path = os.path.join(folder, 'invalid.log')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/upload/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="message">Could not parse these results</li>'
                in output.data)

        # Invalid username
        user = FakeFasUser()
        user.username = 'kerneltest'
        with user_set(app.APP, user):
            full_path = os.path.join(folder, 'invalid.log')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'csrf_token': csrf_token,
            }
            output = self.app.post('/upload/', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">The `kerneltest` username is reserved, '
                'you are not allowed to use it</li>' in output.data)

    def test_upload_results_anonymous(self):
        ''' Test the app.upload_results function for an anonymous user. '''
        folder = os.path.dirname(os.path.abspath(__file__))
        filename = '2.log'

        user = None
        with user_set(app.APP, user):
            output = self.app.get('/upload/')
            self.assertEqual(output.status_code, 302)
            self.assertTrue('<title>Redirecting...</title>' in output.data)

        user = None
        with user_set(app.APP, user):
            output = self.app.get('/upload/anonymous')
            self.assertEqual(output.status_code, 405)
            self.assertTrue(
                '<title>405 Method Not Allowed</title>' in output.data)

            full_path = os.path.join(folder, filename)
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
            }
            output = self.app.post('/upload/', data=data)
            self.assertEqual(output.status_code, 302)
            self.assertTrue('<title>Redirecting...</title>' in output.data)

            # Invalid request
            data = {
                'username': 'pingou',
            }
            output = self.app.post('/upload/anonymous', data=data)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.data)
            exp = {
                "error": "Invalid request",
                "messages": {
                    "test_result": [
                        "This field is required."
                    ]
                }
            }
            self.assertEqual(data, exp)

            # Invalid username

            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'kerneltest',
            }
            output = self.app.post('/upload/anonymous', data=data)
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.data)
            exp = {
                'error': 'The `kerneltest` username is reserved, you are '
                'not allowed to use it'
            }
            self.assertEqual(data, exp)

            # Valid and successful upload
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
            }
            output = self.app.post('/upload/anonymous', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            self.assertEqual(data, {'message': 'Upload successful!'})

            # Invalid file upload
            full_path = os.path.join(folder, 'invalid.log')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'ano',
            }
            output = self.app.post('/upload/anonymous', data=data)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.data)
            exp = {"error": "Invalid input file"}
            self.assertEqual(data, exp)

            # Invalid mime type uploaded
            full_path = os.path.join(folder, 'denied.png')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'ano',
            }
            output = self.app.post('/upload/anonymous', data=data)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.data)
            exp = {"error": "Invalid input file"}
            self.assertEqual(data, exp)

    def test_upload_results_autotest(self):
        ''' Test the app.upload_results function for the autotest user. '''
        folder = os.path.dirname(os.path.abspath(__file__))
        filename = '3.log'
        full_path = os.path.join(folder, filename)

        user = None
        with user_set(app.APP, user):
            output = self.app.get('/upload/autotest')
            self.assertEqual(output.status_code, 405)
            self.assertTrue(
                '<title>405 Method Not Allowed</title>' in output.data)

            # Not logged in, /upload/ not allowed
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
            }
            output = self.app.post('/upload/', data=data)
            self.assertEqual(output.status_code, 302)
            self.assertTrue('<title>Redirecting...</title>' in output.data)

            # Missing the api_token field
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
            }
            output = self.app.post('/upload/autotest', data=data)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.data)
            exp = {
                "error": "Invalid request",
                "messages": {
                    "api_token": [
                        "This field is required."
                    ]
                }
            }
            self.assertEqual(data, exp)

            # Invalid api_token
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'api_token': 'foobar',
            }
            output = self.app.post('/upload/autotest', data=data)
            self.assertEqual(output.status_code, 401)
            data = json.loads(output.data)
            exp = {"error": "Invalid api_token provided"}
            self.assertEqual(data, exp)

            # Valid api_token
            app.APP.config['API_KEY'] = 'api token for the tests'
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'api_token': 'api token for the tests',
            }
            output = self.app.post('/upload/autotest', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            exp = {"message": "Upload successful!"}
            self.assertEqual(data, exp)

            # Second valid upload
            full_path = os.path.join(folder, '4.log')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'api_token': 'api token for the tests',
            }
            output = self.app.post('/upload/autotest', data=data)
            self.assertEqual(output.status_code, 200)
            data = json.loads(output.data)
            exp = {"message": "Upload successful!"}
            self.assertEqual(data, exp)

            # Invalid file upload
            full_path = os.path.join(folder, 'invalid.log')
            stream = open(full_path)
            data = {
                'test_result': stream,
                'username': 'pingou',
                'api_token': 'api token for the tests',
            }
            output = self.app.post('/upload/autotest', data=data)
            self.assertEqual(output.status_code, 400)
            data = json.loads(output.data)
            exp = {"error": "Invalid input file"}
            self.assertEqual(data, exp)

    def test_stats(self):
        ''' Test the stats method. '''
        self.test_upload_results_autotest()
        self.test_upload_results_anonymous()
        self.test_upload_results_loggedin()

        output = self.app.get('/stats')
        data = output.data.split('\n')
        self.assertEqual(data[59], '    <th>Number of tests</th>')
        self.assertEqual(data[60], '    <td>5</td>')
        self.assertEqual(data[64], '    <td>1</td>')
        self.assertEqual(data[68], '    <td>1</td>')
        self.assertEqual(
            output.data.count('<td>3.14.1-200.fc20.x86_64</td>'), 1)

    def test_index(self):
        ''' Test the index method. '''
        self.test_upload_results_autotest()
        self.test_upload_results_anonymous()
        self.test_upload_results_loggedin()
        self.test_admin_new_release()

        output = self.app.get('/')
        self.assertTrue(
            "<a href='/kernel/3.14.1-200.fc20.x86_64'>" in output.data)
        self.assertTrue("<a href='/release/20'>" in output.data)

    def test_release(self):
        ''' Test the release method. '''
        self.test_upload_results_autotest()
        self.test_upload_results_anonymous()
        self.test_upload_results_loggedin()
        self.test_admin_new_release()

        output = self.app.get('/release/20')
        self.assertTrue(
            "<a href='/kernel/3.14.1-200.fc20.x86_64'>" in output.data)
        self.assertTrue('<h1>Kernels Tested for Fedora </h1>' in output.data)

    def test_kernel(self):
        ''' Test the kernel method. '''
        self.test_upload_results_autotest()
        self.test_upload_results_anonymous()
        self.test_upload_results_loggedin()
        self.test_admin_new_release()

        output = self.app.get('/kernel/3.14.1-200.fc20.x86_64')
        self.assertEqual(
            output.data.count('<img src="/static/Denied.png" />'), 5)
        self.assertTrue("<a href='/logs/1'>" in output.data)
        self.assertTrue("<a href='/logs/2'>" in output.data)
        self.assertTrue("<a href='/logs/3'>" in output.data)
        self.assertTrue("<a href='/logs/4'>" in output.data)
        self.assertTrue("<a href='/logs/5'>" in output.data)

    def test_is_safe_url(self):
        """ Test the is_safe_url function. """
        import flask
        lcl_app = flask.Flask('kerneltest')

        with lcl_app.test_request_context():
            self.assertTrue(app.is_safe_url('http://localhost'))
            self.assertTrue(app.is_safe_url('https://localhost'))
            self.assertTrue(app.is_safe_url('http://localhost/test'))
            self.assertFalse(
                app.is_safe_url('http://fedoraproject.org/'))
            self.assertFalse(
                app.is_safe_url('https://fedoraproject.org/'))

    def test_admin_new_release(self):
        """ Test the admin_new_release function. """
        user = None
        with user_set(app.APP, user):
            output = self.app.get('/admin/new', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<title>OpenID transaction in progress</title>'
                in output.data)

        user = FakeFasUser()
        user.groups = []
        user.cla_done = False
        with user_set(app.APP, user):
            output = self.app.get('/admin/new', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">You are not an admin</li>' in output.data)

        user = FakeFasUser()
        user.groups = []
        with user_set(app.APP, user):
            output = self.app.get('/admin/new', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="error">You are not an admin</li>' in output.data)

        user = FakeFasUser()
        user.groups.append('sysadmin-main')
        with user_set(app.APP, user):
            output = self.app.get('/admin/new')
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<title> New release' in output.data)
            self.assertTrue(
                "<label for=\"releasenum\">Release number <span "
                "class='error'>*</span></label>" in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'csrf_token': csrf_token,
                'releasenum': 20,
                'support': 'RELEASE',
            }

            output = self.app.post(
                '/admin/new', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue(
                '<li class="message">Release &#34;20&#34; added</li>'
                in output.data)
            self.assertTrue("<a href='/release/20'>" in output.data)
            self.assertTrue("<a href='/admin/20/edit'" in output.data)


if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(KerneltestTests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)
