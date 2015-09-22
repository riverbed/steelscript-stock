# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from setuptools import setup, find_packages
from gitpy_versioning import get_version

install_requires = (
    'steelscript.appfwk',
)

setup_args = {
    'name':                'steelscript.stock',
    'namespace_packages':  ['steelscript'],
    'version':             get_version(),
    'author':             'Riverbed Technology',
    'author_email':       'eng-github@riverbed.com',
    'url':                'http://pythonhosted.org/steelscript',
    'license':             'MIT',
    'description':         'Stock Report plugin for SteelScript Application Framework',
    'long_description':    """\
Stock Report for SteelScript Application Framework
==================================================

SteelScript is a collection of libraries and scripts in Python and JavaScript
for interacting with Riverbed Technology devices.

This package demonstrates how an external data source can be incorporated
as a plugin to App Framework, with associated reports.

For a complete guide to installation, see:

http://pythonhosted.org/steelscript/
    """,

    'packages': find_packages(exclude=('gitpy_versioning',)),
    'zip_safe': False,
    'install_requires': install_requires,
    'extras_require': None,
    'test_suite': '',
    'include_package_data': True,
    'entry_points': {
        'portal.plugins': [
            'stock = steelscript.stock.appfwk.plugin:Plugin'
        ],
    },

    'classifiers': (
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ),
}

setup(**setup_args)
