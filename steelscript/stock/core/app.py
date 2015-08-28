# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import datetime

from pprint import pprint

from steelscript.common.app import Application
from steelscript.common.timeutils import TimeParser
from steelscript.common.connection import Connection
from steelscript.common.exceptions import RvbdHTTPException

# Mapping from price measure to the relative position
# in the response string
mapping = {'open': 1,
           'high': 2,
           'low': 3,
           'close': 4,
           'volume': 5}

tp = TimeParser()


class StockApiException(Exception):
    pass


def parse_date(date):
    return tp.parse(date + " 00:00")


def get_historical_prices(begin, end, symbol, measures,
                          resolution='day', date_obj=False):
    """Get historical prices for the given ticker symbol.
    Returns a list of dicts keyed by 'date' and measures

    :param string begin: begin date of the inquire interval
      in the format of YYYY-MM-DD
    :param string end: end date of the inquire interval
      in the format of YYYY-MM-DD
    :param string symbol: symbol of one stock to query
    :param list measures: a list of prices that needs to be queried,
      should be a subset of ["open", "high", "low", "close", "volume"]
    :param string resolution: '1 day' or '5 days'
    :param boolean date_obj: dates are converted to datetime objects
      from date strings if True. Otherwise, dates are stored as strings
    """
    try:
        conn = Connection('http://ichart.finance.yahoo.com')
        start_month = parse_date(begin).month - 1
        start_day = parse_date(begin).day
        start_year = parse_date(begin).year
        end_month = parse_date(end).month - 1
        end_day = parse_date(end).day
        end_year = parse_date(end).year

        ret = []
        params = {'s': symbol,
                  'a': start_month,
                  'b': start_day,
                  'c': start_year,
                  'd': end_month,
                  'e': end_day,
                  'f': end_year,
                  'g': resolution[0],
                  'ignore': '.csv'}

        resp = conn.request(method='POST', path='/table.csv', params=params)
        # extract data and skip first row with column titles
        data = list(resp.iter_lines())[1:]

        # iterate over the data backwards as the daily prices are sorted
        # backwards by the dates
        for day in reversed(data):
            # day is a string with date, prices, volume separated by commas,
            # '<date>,<open>,<high>,<low>,<close>,<volume>,<adj_close>'
            # as '2014-02-19,20.22,20.55,20.11,20.50,1599600,20.50'
            day = day.split(',')
            date = parse_date(day[0]) if date_obj else day[0]
            daily_prices = {'date': date}
            for m in measures:
                if m in mapping:
                    daily_prices[m] = float(day[mapping[m]])
            ret.append(daily_prices)
    except RvbdHTTPException:
        raise StockApiException("Symbol '%s' is invalid or Stock '%s' was"
                                " not on market on %s" % (symbol, symbol,
                                                          end))
    return ret


class StockApp(Application):

    today = str(datetime.datetime.now().date())

    def add_options(self, parser):
        super(StockApp, self).add_options(parser)

        parser.add_option('-b', '--begin', help='begin date as YYYY-MM-DD')
        parser.add_option('-e', '--end', help='end date as YYYY-MM-DD',
                          default=self.today)

        parser.add_option('-r', '--resolution', default='day',
                          help='day or week')
        parser.add_option('-s', '--symbol', help='symbol of the stock')
        parser.add_option('-m', '--measures',
                          help=("list of measures to inquire, "
                                "such as open, high, low, close, volume, "
                                "delimited by commas"))

    def validate_args(self):
        super(StockApp, self).validate_args()

        if not self.options.symbol:
            self.parser.error("Symbol needs to be specified")

        if not self.options.measures:
            self.parser.error("Measures needs to be specified")
        else:
            measures = self.options.measures.split(',')
            for measure in measures:
                if measure not in ['open', 'high', 'low', 'close', 'volume']:
                    self.parser.error("Invalid measure %s" % measure)

        if self.options.resolution not in ['day', 'week']:
            self.parser.error("Invalid resolution %s" %
                              self.options.resolution)

        if not self.options.begin:
            self.parser.error("Begin date needs to be specified")
        else:
            try:
                begin_date = parse_date(self.options.begin)
            except:
                self.parser.error("Begin date %s is invalid" %
                                  self.options.begin)

        try:
            end_date = parse_date(self.options.end)
        except:
            self.parser.error("End date %s is invalid" % self.options.end)

        # begin date should be less than the both today and end date
        if begin_date > min(end_date, parse_date(self.today)):
            self.parser.error("Begin date %s is later than either "
                              "today's date %s or end date %s" %
                              (begin_date, self.today, end_date))

    def main(self):
        pprint(get_historical_prices(self.options.begin,
                                     self.options.end,
                                     self.options.symbol,
                                     self.options.measures.split(','),
                                     self.options.resolution))
if __name__ == '__main__':
    StockApp().run()
