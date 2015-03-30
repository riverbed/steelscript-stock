# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import urllib
import datetime

from pprint import pprint

from steelscript.common.app import Application
from steelscript.common.timeutils import TimeParser

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
                          resolution='1 day', date_obj=False):
    """Get historical prices for the given ticker symbol.
    Returns a list of dicts keyed by 'date' and measures

    :param string begin: begin date of the inquire interval
    :param string end: end date of the inquire interval
    :param string symbol: symbol of one stock to query
    :param list measures: a list of prices that needs to be queried,
    should be a subset of ["open", "high", "low", "close", "volume"]
    :param string resolution: '1 day' or '5 days'
    :param boolean date_obj: dates are converted to datetime objects
    from date strings if True. Otherwise, dates are stored as strings
    """
    try:
        reso = 'w' if str(resolution)[0:6] == '5 days' else 'd'
        url = ('http://ichart.finance.yahoo.com/table.csv?s=%s&' % symbol +
               'a=%s&' % str(int(begin[5:7]) - 1) +
               'b=%s&' % str(int(begin[8:10])) +
               'c=%s&' % str(int(begin[0:4])) +
               'd=%s&' % str(int(end[5:7]) - 1) +
               'e=%s&' % str(int(end[8:10])) +
               'f=%s&' % str(int(end[0:4])) +
               'g=%s&' % reso +
               'ignore=.csv')
        ret = []
        days = urllib.urlopen(url).readlines()
        for day in reversed(days[1:]):
            day = day[:-2].split(',')
            date = parse_date(day[0]) if date_obj else day[0]
            daily_prices = {'date': date}
            for m in measures:
                if m in mapping:
                    daily_prices[m] = float(day[mapping[m]])
            ret.append(daily_prices)
    except IndexError:
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

        parser.add_option('-r', '--resolution', default='daily',
                          help='daily or weekly')
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

        if self.options.resolution not in ['daily', 'weekly']:
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
        rsl = '5 days' if self.options.resolution == 'weekly' else '1 day'
        pprint(get_historical_prices(self.options.begin,
                                     self.options.end,
                                     self.options.symbol,
                                     self.options.measures.split(','),
                                     rsl))
if __name__ == '__main__':
    StockApp().run()
