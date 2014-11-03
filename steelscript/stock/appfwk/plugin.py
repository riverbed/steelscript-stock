# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import pkg_resources

from steelscript.appfwk.apps.plugins import Plugin as AppsPlugin


class Plugin(AppsPlugin):
    title = 'stock chart'
    description = 'simple stock report'
    version = pkg_resources.get_distribution('steelscript.stock').version
    author = 'wg'

    enabled = True
    can_disable = True

    devices = ['devices']
    datasources = ['datasources']
    reports = ['reports']
