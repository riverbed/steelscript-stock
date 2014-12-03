# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
	# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""This file defines a basic stock price generator."""
					

import random
import datetime

DAY_SECONDS = 86400

class StockGenerator(object):
    
    def generate(self, t0, t1, measures, prices, resolution=1, progress=None):
	"""Generate a set of prices.
				
	:param int t0: start time in epoch seconds
	:param int t1: endtime in epoch seconds
	:param int resolution: distance between points in seconds
	:param list stocks: list of quote objects
	:param list prices: list of daily prices, each consists open, high, low, close prices
	:param func progress: optional function to call to update progress

	:returns: list of lists of data values

	This function computes a series of prices and returns
	a list of rows.  Each row is comprised of the timestamp (epoch
	seconds) followed by one floating point value for each stock.

	"""

	rows = []
	t = t0
	while t < t1:
		row = []
		date_str = str(datetime.datetime.fromtimestamp(t))[:10]
		if date_str in prices:
			row.append(date_str)
	
			for measure in measures:
				row.append(prices[date_str][measure])
	
			rows.append(row)
		t = t + resolution

		if progress:
			progress(100*(float(t)-float(t0))/(float(t1)-(t0)))

	return rows
