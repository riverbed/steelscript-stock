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
import urllib

from steelscript.common.timeutils import TimeParser
from steelscript.appfwk.apps.datasource.models import \
    DatasourceTable, TableQueryBase, Column, TableField

from steelscript.appfwk.apps.datasource.forms import (
    fields_add_time_selection, fields_add_resolution,
    DateTimeField, ReportSplitDateWidget)

from steelscript.stock.core.stock import get_historical_prices

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
                     'resolution': '1d',
                     'resolutions': ('1d', '5d')
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
        self.fields_add_end_date('end_date', 'now-0')

    def fields_add_stock_symbol(self, help_text, keyword='stock_symbol',
                                initial=None):
        field = TableField(keyword=keyword,
                           label='Stock Symbol',
                           help_text=(help_text),
                           initial=initial,
                           required=True)
        field.save()
        self.fields.add(field)

    def fields_add_end_date(self, keyword, initial_end_date):
        field = TableField(keyword=keyword,
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

        # Time selection is available via criterai.starttime and endtime.
        # These are date time strings in the format of YYYY-MM-DD
        self.t0 = str(criteria.end_date - criteria.duration)[:10]
        self.t1 = str(criteria.end_date)[:10]

        # Time resolution is a timedelta object
        self.resolution = criteria.resolution

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
            if len(self.data) >= len(his):
                for i in range(len(his)):
                    # merging the new ticker daily price
                    merged = dict(self.data[-len(his)+i].items() +
                                  his[i].items())
                    self.data[-len(his)+i] = merged
            else:
                # len(self.data)<len(his)
                # current stock has less history than previous ones
                for i in range(len(self.data)):
                    merged = dict(self.data[i].items() +
                                  his[-len(self.data)+i].items())
                    his[-len(self.data)+i] = merged
                self.data = his

    def run_query(self, measure=None):
        # delete non-key columns associated with table
        for c in self.table.get_columns():
            if not c.iskey:
                c.delete()

        for ticker in self.symbol.split(","):
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
