#!/usr/bin/env python

"""
Setup script
"""

# Required to build on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

from setuptools import setup
from kerneltest.app import __version__


setup(
    name='kerneltests',
    description='kerneltests is a web application meant to collect results '
                'from kernel tests.',
    version=__version__,
    author='Justin M. Forbes & Pierre-Yves Chibon',
    author_email='jmforbes@linuxtx.org, pingou@pingoured.fr',
    maintainer='Pierre-Yves Chibon',
    maintainer_email='pingou@pingoured.fr',
    license='GPLv2',
    download_url='https://github.com/jmflinuxtx/kerneltest-harness/archive/master.tar.gz',
    url='https://github.com/jmflinuxtx/kerneltest-harness/',
    packages=['kerneltest'],
    include_package_data=True,
    install_requires=[
        'Flask', 'SQLAlchemy>=0.6', 'wtforms', 'flask-wtf',
        'python-fedora', 'python-openid', 'python-openid-teams',
        'python-openid-cla'],
)
