from alpaca_indicators import SMA, ATR
from alpaca_api import Alpaca, AlpacaStreaming, get_symbols
from alpaca_monitor import live_monitoring
from utils import key, get_time_info
from datetime import datetime

import numpy as np
import pandas as pd
import time
import json
import threading




# Main class: AlpacaTrade

class AlpacaTrade(object):

  def __init__(self,api_key, api_secret, allow_daytrading=False,
               needed_periods=8, max_positions=4, bar_period='1D',
               stop_loss=None, take_profit=None, data_limit=200):

    """
      bar_period:   ['1D', '15Min', '5Min', '1Min'],
      stop_loss:    float between 1 - 0
      take_profit:  float between 1 - inf
      data_limit:   1000 - 200
    """
    self.daytrading = allow_daytrading
    self.apc = Alpaca(api_key, api_secret)
    self.apc_stream = AlpacaStreaming(api_key, api_secret)
    self.needed_periods = needed_periods
    self.max_positions = max_positions
    self.bar_period = bar_period
    self.data_limit = data_limit
    self.stop_loss = stop_loss
    self.take_profit = take_profit

    self.data = None
    self.symbols = []
    self.positions = []
    self.orders = []
    self.pending_orders = []
    self.buying_power = 0

  def iterate(self):
    self.get_account_info()

    if len(self.positions) == self.max_positions:
      print('Already in max number of positions - skipping iteration.')
      return

    self.symbols = [tick['symbol'] for tick in get_symbols(screener=self.screener)]
    self.data = self.apc.historical_data(self.symbols, tf=self.bar_period, limit=self.data_limit)
    self.indicators()

    for symbol in self.symbols:
      if not self.check_data(symbol):
        print(f'{symbol} has no data - consider manually filtering out in screener.')
        continue

      price = self.apc.get_last_trade(symbol)['last']['price']

      if self.analyzer(symbol, price):
        if self.check_status('positions', symbol) or self.check_status('orders', symbol):
          continue

        qty = self.get_qty(price)

        if qty == 0:
          break

        self.pending_orders.append({'symbol': symbol, 'qty': qty, 'price': price})
        self.buying_power = self.buying_power - float(price * 1.01) * qty

    self.trade()


  def run(self, iterate_every=60*1):
    while True:
      market = apc.get_clock()

      if market['is_open']:
        print('\n :: Markets are OPEN. Running algorithm. ')
        self.algorithm(iterate_every)

      print('\n :: Markets are CLOSED. Sleeping. ')

      market = apc.get_clock()
      seconds = get_time_info(market)

      time.sleep(seconds)

  def algorithm(self, iterate_every):
    iteration_start_time = time.time()
    iteration = 0

    if not self.allow_daytrading:
      live_monitoring_thread = threading.Thread(
        target=live_monitoring,
        args=(self),
        daemon=True
      )
      live_monitoring_thread.start()

    while True:
      iteration += 1
      print('\n\n:: Iteration {} at {}'.format(iteration, time.strftime("%Y-%m-%d %H:%M:%S")))
      market = self.apc.get_clock()
      # current_hour = datetime.now().hour + 3
      # current_minute = (datetime.now().minute / 100)
      # closing_time = datetime.fromisoformat(market['next_close']).hour - .40
      # till_close = closing_time - (current_hour + current_minute)

      if not market['is_open']:
        break

      self.iterate()

      print(':: Finished iteration {} at {}'.format(iteration, time.strftime(template)))
      time.sleep(iterate_every - ((time.time() - iteration_start_time) % iterate_every))


  def get_account_info(self):
    self.positions = apc.get_positions()
    self.orders = apc.get_orders(status='open')
    self.buying_power = float(apc.get_account()['buying_power'])

  def indicator(self, func, **kwargs):
    self.data = func(self.data, **kwargs)

  def indicators(self):
    """ Initializes indicators """
    pass

  def screener(self, ticker):
    """
      `ticker` keys: ['lastsale', 'symbol', 'exchange', 'pctchange']
       Return: boolean =>  ..to determine if the ticker passes the screen
    """
    return True

  def analyzer(self, symbol, price):
    """ Return: boolean => ...to determine if it passes the buy conditions """
    return True

  def selector(self):
    """ Return: array => ...of orders (from 'create_order') to be executed """
    return []

  def check_data(self, symbol):
    if symbol not in self.data:
      return False

    self.data[symbol].dropna(inplace=True)

    return True if len(self.data[symbol]) < self.needed_periods else False

  def check_status(self, typs, symbol):
    for typ in getattr(self, typs):
      if key(typ, 'symbol') == symbol and key(typ, 'qty') != 0:
        return True

    return False

  def get_qty(self, price):
    if self.max_positions == len(self.positions):
      return 0

    return max(1, int((self.buying_power / self.max_positions) / price))

  def trade(self):
    for order in self.selector():
      if not self.allow_daytrading:
        print('Placing a buy order for {} {}'.format(order['qty'], order['symbol']))
        apc.buy(order['symbol'], order['qty'])
        continue

      if self.allow_daytrading and self.stop_loss and self.take_profit:
        print('Placing a bracket order for {} {}'.format(order['qty'], order['symbol']))
        apc.bracket_order(
          order['symbol'], order['qty'], order['price'] * self.take_profit,
          order['price'] * self.stop_loss, tif='gtc'
        )





# Example



class StackOne(AlpacaTrade):
  short_sma = 20
  long_sma = 200

  def indicators(self):
    self.indicator(SMA, periods=short_sma)
    self.indicator(SMA, periods=long_sma)
    self.indicator(ATR)

  def screener(self, ticker):
    return ticker['lastsale'] < 8 and ticker['lastsale'] > 1

  def analyzer(self, symbol, price):
    price_week_ago = self.data[symbol][f'{short_sma}_sma'].iloc[-5]
    pct_change = round(((price / price_week_ago) - 1) * 100, 2)

    dropped_enough = pct_change <= -15.00
    short_is_above = self.data[symbol][f'{short_sma}_sma'].iloc[-1] > self.data[symbol][f'{long_sma}_sma'].iloc[-1]

    return dropped_enough and short_is_above

  def selector(self):
    for order in self.orders:
      symbol = order['symbol']
      avg_volatility = sum(self.data[symbol]['ATR'].iloc[-10:]) / 10
      order['volatility'] = avg_volatility

    sorted_orders = sorted(self.orders, key=lambda x: x['volatility'], reverse=True)

    return sorted_orders[:self.max_positions]



# bryantleebrock@gmail.com paper account
auth = {
  'api_key': 'PK0ZTJY4V309PKX2DNVI',
  'secret_key': 'X4s2I5tiyRavpHl9Rre8SvNuiO8Huxjh5AsFE07e',
}

apc_trade = StackOne(
  auth['api_key'],
  auth['secret_key'],
  allow_daytrading=False,
  max_positions=2, stop_loss=0.70,
  take_profit=1.06, data_limit=200
)

apc_trade