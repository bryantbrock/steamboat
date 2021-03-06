from ..alpaca_modules.alpaca_indicators import *
from ..alpaca_modules.alpaca_api import Alpaca, get_symbols


# Main class: AlpacaScreen

class AlpacaScreen:

  def __init__(self, api_key, secret_key, periods='1D',
               paper=False, data_limit=200,
               needed_periods=14, exchanges=['nyse', 'nasdaq', 'amex']):

    """
      periods    : '1D', '15Min', '5Min', '1Min'
      data_limit :  200 - 1000
    """

    self.apc = Alpaca(api_key, secret_key, paper=paper)
    self.periods = periods
    self.data_limit = data_limit
    self.needed_periods = needed_periods
    self.exchanges = exchanges

    self.data = None
    self.symbols = []

  def run(self):
    self.symbols = [tick['symbol'] for tick in get_symbols(
      exchanges=self.exchanges, screener=self.stock_screen
    )]
    self.data = self.apc.historical_data(self.symbols, tf=self.periods, limit=self.data_limit)
    self.indicators()

    for symbol in self.symbols:
      if not self.check_data(symbol):
        continue

      self.analyze(symbol, self.data[symbol]['close'].iloc[-1])

  def indicator(self, func, *args, **kwargs):
    self.data = func(self.data, *args, **kwargs)

  def check_data(self, symbol):
    if symbol not in self.data:
      return False

    self.data[symbol].dropna(inplace=True)

    if self.data[symbol].empty:
      return False

    if len(self.data[symbol]) < self.needed_periods:
      return False

    return True

  # Custom functions

  def indicators(self):
    pass

  def stock_screen(self, ticker):
    pass

  def analyze(self, symbol, price):
    pass