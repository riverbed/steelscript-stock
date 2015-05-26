# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

"""
This file defines a data source for querying data.

There are three parts to defining a data source:

* Defining column options via a Column class
* Defining table options via a DatasourceTable
* Defining the query mechanism via TableQuery

Note that you can define multiple Column and Table classes
in the same file, but only one TableQuery.  If you need
to define multiple types of queries, create multiple
files in this directory named accordingly.

"""

import logging

from steelscript.appfwk.apps.datasource.models import \
    DatasourceTable, TableQueryBase, Column, TableField

from steelscript.appfwk.apps.datasource.forms import (
    fields_add_time_selection, fields_add_resolution,
    DateTimeField, ReportSplitDateWidget)

from steelscript.stock.core.app import get_historical_prices

logger = logging.getLogger(__name__)


class StockColumn(Column):
    class Meta:
        proxy = True

    COLUMN_OPTIONS = {}


class StockTable(DatasourceTable):
    class Meta:
        proxy = True

    _column_class = 'StockColumn'
    FIELD_OPTIONS = {'duration': '4w',
                     'durations': ('4w', '12w', '24w', '52w', '260w', '520w'),
                     'resolution': 'day',
                     'resolutions': ('day', 'week')
                     }

    def post_process_table(self, field_options):
        # Add a time selection field
        fields_add_time_selection(self, show_end=False,
                                  initial_duration=field_options['duration'],
                                  durations=field_options['durations'])

        # Add time resolution selection
        fields_add_resolution(self,
                              initial=field_options['resolution'],
                              resolutions=field_options['resolutions'])

        # Add end date field
        self.fields_add_end_date()

    def fields_add_stock_symbol(self, help_text, keyword='stock_symbol',
                                initial=None):
        field = TableField(keyword=keyword,
                           label='Stock Symbol',
                           help_text=(help_text),
                           initial=initial,
                           required=True)
        field.save()
        self.fields.add(field)

    def fields_add_end_date(self, initial_end_date='now-0'):
        # Add a date field
        # the front javascript code will determine the default date
        # according to initial_end_date, so if initial_end_date is
        # 'now-0', today will be the default end date
        field = TableField(keyword='end_date',
                           label='End Date',
                           field_cls=DateTimeField,
                           field_kwargs={'widget': ReportSplitDateWidget,
                                         'widget_attrs': {'initial_date':
                                                          initial_end_date}},
                           required=False)
        field.save()
        self.fields.add(field)


class SingleStockTable(StockTable):
    """Table class associated with report showing stock prices
    for a single stock, including open, high, low, close prices.
    """
    class Meta:
        proxy = True

    _query_class = 'SingleStockQuery'

    TABLE_OPTIONS = {'stock_symbol': None}

    def post_process_table(self, field_options):
        super(SingleStockTable, self).post_process_table(field_options)

        # Add stock symbol
        self.fields_add_stock_symbol('Single ticker symbol')


class MultiStockTable(StockTable):
    """Table class associated with report showing close prices
    for the given date range for input multiple stocks.
    """
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'stock_symbol': None}

    def post_process_table(self, field_options):
        super(MultiStockTable, self).post_process_table(field_options)

        # Add stock symbol
        self.fields_add_stock_symbol('Ticker symbols separated by commas')


class MultiStockPriceTable(MultiStockTable):
    class Meta:
        proxy = True

    _query_class = 'MultiStockPriceQuery'


class MultiStockVolumeTable(MultiStockTable):
    class Meta:
        proxy = True

    _query_class = 'MultiStockVolumeQuery'


class StockQuery(TableQueryBase):

    def prepare(self):
        """Prepare data for query to run"""
        criteria = self.job.criteria

        # These are date time strings in the format of YYYY-MM-DD
        self.t0 = str((criteria.end_date - criteria.duration).date())
        self.t1 = str(criteria.end_date.date())

        # Resolution is either day or week
        self.resolution = ('day' if str(criteria.resolution).
                           startswith('1 day') else 'week')

        # stock symbol string (can have multiple symbol)
        self.symbol = criteria.stock_symbol

        # Dict storing stock prices/volumes according to specific report
        self.data = []

    def get_data(self, symbol, measures, date_obj=False):
        return get_historical_prices(self.t0, self.t1, symbol, measures,
                                     self.resolution, date_obj=date_obj)


class SingleStockQuery(StockQuery):
    """Single stock query class used by candle stick widget
    to print graph that shows four prices of one stock for
    each day. Four prices include open, high, low, close prices.
    """
    def run(self):
        self.prepare()
        measures = ["open", "high", "low", "close"]
        self.data = self.get_data(self.symbol, measures)
        return True


class MultiStockQuery(StockQuery):
    """Base query class to fetch prices for multiple stocks"""
    def prepare(self):
        super(MultiStockQuery, self).prepare()

    def merge_price_history(self, his):
        """Merge history of another stock with self.data"""
        if not self.data:
            self.data = his
        else:
            # As some stock might be off market on certain random days
            # thus merging the dicts need to be done according to date
            # As the stock data is sorted based on date
            # while neither lists (self.data and his) is empty
            # pop the first elements of the each list
            # if the dates are the same, merging them into one dict,
            # append to merged, if not the same, append the dict with
            # smaller dates and then the other to merged. when one
            # list is empty, just append the other list to merged
            merged = []
            while self.data and his:
                rec1 = self.data[0]
                rec2 = his[0]
                if rec1['date'] == rec2['date']:
                    rec1.update(rec2)
                    merged.append(rec1)
                    self.data.pop(0)
                    his.pop(0)
                elif rec1['date'] < rec2['date']:
                    merged.append(rec1)
                    self.data.pop(0)
                else:
                    merged.append(rec2)
                    his.pop(0)
            merged.extend(self.data)
            merged.extend(his)
            self.data = merged

    def run_query(self, measure=None):
        # delete non-key columns associated with table
        for c in self.table.get_columns():
            if not c.iskey:
                c.delete()

        for ticker in self.symbol.split(","):
            # strip white spaces
            ticker = ticker.strip()
            StockColumn.create(self.table, ticker, ticker.upper())
            if measure is None:
                measure = "close"
            history = self.get_data(ticker, [measure], date_obj=True)
            for day in history:
                # replace history price measure key with ticker
                day[ticker] = day[measure]
                del day[measure]
            self.merge_price_history(history)
        return True


class MultiStockPriceQuery(MultiStockQuery):
    """Query to fetch one measure of stock prices for multiple stocks"""
    def run(self):
        super(MultiStockPriceQuery, self).prepare()
        return self.run_query()


class MultiStockVolumeQuery(MultiStockQuery):
    """Query to fetch daily volumes for multiple stocks"""
    def run(self):
        super(MultiStockVolumeQuery, self).prepare()
        return self.run_query("volume")
