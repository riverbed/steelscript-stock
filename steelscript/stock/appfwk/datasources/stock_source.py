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

from steelscript.appfwk.apps.devices.forms import fields_add_device_selection
from steelscript.appfwk.apps.datasource.forms import (
    fields_add_time_selection, fields_add_resolution,
    DateTimeField, ReportSplitDateWidget)

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
        # Add a device field
        fields_add_device_selection(self, keyword='stock_device',
                                    label='Device', module='stock_device',
                                    enabled=True)

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

        # Check that a stock_device was selected
        if criteria.stock_device == '':
            logger.debug('%s: No stock device selected' % self.table)
            self.job.mark_error("No Stock Device Selected")
            return False

        # Time selection is available via criterai.starttime and endtime.
        # These are date time strings in the format of YYYY-MM-DD
        self.t0 = str(criteria.end_date - criteria.duration)[:10]
        self.t1 = str(criteria.end_date)[:10]

        # Time resolution is a timedelta object
        self.resolution = criteria.resolution

        # stock symbol string (can have multiple symbol)
        self.symbol = criteria.stock_symbol

        # Mapping from price measure to the relative position
        # in the response string
        self.mapping = {'open': 1,
                        'high': 2,
                        'low': 3,
                        'close': 4,
                        'volume': 5}

        # Dict storing stock prices/volumes according to specific report
        self.data = []

    def get_historical_prices(self, symbol, measures, date_obj=False):
        """Get historical prices for the given ticker symbol.
        Returns a list of dicts keyed by 'date' and measures

        :param string symbol: symbol of one stock to query
        :param list measures: a list of prices that needs to be queried,
        should be a subset of ["open", "high", "low", "close", "volume"]
        :param boolean date_obj: dates are converted to datetime objects
        from date strings if True. Otherwise, dates are stored as strings
        """
        try:
            # obtain time parser object if date_obj is True
            tp = TimeParser() if date_obj else None
            reso = 'w' if str(self.resolution)[0:6] == '5 days' else 'd'
            url = ('http://ichart.finance.yahoo.com/table.csv?s=%s&' % symbol +
                   'a=%s&' % str(int(self.t0[5:7]) - 1) +
                   'b=%s&' % str(int(self.t0[8:10])) +
                   'c=%s&' % str(int(self.t0[0:4])) +
                   'd=%s&' % str(int(self.t1[5:7]) - 1) +
                   'e=%s&' % str(int(self.t1[8:10])) +
                   'f=%s&' % str(int(self.t1[0:4])) +
                   'g=%s&' % reso +
                   'ignore=.csv')
            ret = []
            days = urllib.urlopen(url).readlines()
            for day in reversed(days[1:]):
                day = day[:-2].split(',')
                date = tp.parse(day[0] + ' 00:00') if tp else day[0]
                daily_prices = {'date': date}
                for m in measures:
                    if m in self.mapping:
                        daily_prices[m] = float(day[self.mapping[m]])
                ret.append(daily_prices)
        except IndexError:
            raise StockApiException("Symbol '%s' is invalid or Stock '%s' was"
                                    " not on market on %s" % (symbol, symbol,
                                                              self.t1))
        return ret


class StockApiException(Exception):
    pass


class SingleStockQuery(StockQuery):
    """Single stock query class used by candle stick widget
    to print graph that shows four prices of one stock for
    each day. Four prices include open, high, low, close prices.
    """
    def run(self):
        self.prepare()
        measures = ["open", "high", "low", "close"]
        self.data = self.get_historical_prices(self.symbol, measures)
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
            history = self.get_historical_prices(ticker, [measure],
                                                 date_obj=True)
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
