from ..alpaca_modules.alpaca_indicators import SMA, ATR
from ..alpaca_modules.alpaca_api import Alpaca, AlpacaStreaming, get_symbols
from .utils import key, get_time_till, StoppableThread
from datetime import datetime
from dotenv import load_dotenv

import numpy as np
import pandas as pd
import time
import json
import threading



# Main class: AlpacaTrade

class AlpacaTrade:

  def __init__(self, api_key, api_secret, allow_daytrading=False,
               needed_periods=8, max_positions=4, log=False,
               bar_period='1D', paper=False, stop_loss=None,
               take_profit=None, data_limit=200):

    """
      bar_period:   ['1D', '15Min', '5Min', '1Min'],
      stop_loss:    float between 1 - 0
      take_profit:  float between 1 - inf
      data_limit:   1000 - 200
    """
    self.allow_daytrading = allow_daytrading
    self.apc = Alpaca(api_key, api_secret, paper=paper, log=log)
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

    self.stream = None
    self.streams = []

  def iterate(self):
    """
    This contains most of the pipline logic. Everything from fetching
    the necessary data to preping the obj for screening, analyzing,
    and selecting.
    """

    try:
      self.get_account_info()
    except:
      print('   Account credentials are invalied.')
      return

    if len(self.positions) == self.max_positions:
      return

    buy_orders = []
    for order in self.orders:
      if order['side'] == 'buy':
        buy_orders.append(order)

    if len(self.orders) == self.max_positions and len(buy_orders) == self.max_positions:
      return

    print('::::: Start analyzing stocks at {}'.format(time.strftime("%Y-%m-%d %H:%M:%S")))

    self.symbols = [tick['symbol'] for tick in get_symbols(screener=self.screener)]
    self.data = self.apc.historical_data(self.symbols, tf=self.bar_period, limit=self.data_limit)
    self.indicators()

    for symbol in self.symbols:
      if not self.check_data(symbol):
        print(f'   {symbol} has no data - consider manually filtering out in screener.')
        continue

      price = self.apc.get_last_trade(symbol)['last']['price']

      if self.analyzer(symbol, price):
        if self.check_status('positions', symbol) or self.check_status('orders', symbol):
          continue

        qty = self.get_qty(price)

        if qty == 0:
          break

        self.pending_orders.append({'symbol': symbol, 'qty': qty, 'price': price})

    self.trade()
    print('::::: Complete analyzing stocks at {}'.format(time.strftime("%Y-%m-%d %H:%M:%S")))


  def run(self, iterate_every=60*1, run_during_market=True,
          minutes_after_open=20, minutes_till_close=1):
    """
    The primary method of `AlpacaTrade`: call it to run the algorithm
    during market hours. If you wish to run it all the time and not check
    for market hours, set `run_during_market=False`.
    """

    while True:
      live_monitoring_thread = StoppableThread(target=self.live_monitoring, daemon=True)
      market = self.apc.get_clock()

      if market['is_open'] or not run_during_market:

        print('\n::::: Markets are OPEN. Running algorithm. ')
        iteration_start_time = time.time()
        iteration = 0

        if not self.allow_daytrading:
          live_monitoring_thread.start()
        else:
          live_monitoring_thread.stop()

        while True:
          iteration += 1
          market = self.apc.get_clock()
          seconds = get_time_till(market, till='next_close', log=False)

          if not market['is_open'] and run_during_market:
            break

          if seconds < 60*minutes_till_close and market['is_open'] and run_during_market:
            break

          self.iterate()

          if len(self.positions) == self.max_positions and \
             len(self.streams) == 0 and run_during_market and \
             not self.allow_daytrading:
            break

          time.sleep(iterate_every - ((time.time() - iteration_start_time) % iterate_every))

      print('\n::::: Stopping algorithm. ')

      if not live_monitoring_thread.stopped():
        live_monitoring_thread.stop()
        print('      ~~Monitoring stopped.')

      market = self.apc.get_clock()
      seconds = get_time_till(market, till='next_open')
      seconds += 60*minutes_after_open

      print(f'\n::::: Sleeping till {minutes_after_open} minutes after next market open. ')
      time.sleep(seconds)


  def get_account_info(self):
    self.positions = self.apc.get_positions()
    self.orders = self.apc.get_orders(status='open')
    self.buying_power = float(self.apc.get_account()['buying_power'])

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
    pass

  def analyzer(self, symbol, price):
    """ Return: boolean => ...to determine if it passes the buy conditions """
    pass

  def selector(self):
    """ Return: array => ...of orders (from 'create_order') to be executed """
    pass


  def check_data(self, symbol):
    if symbol not in self.data:
      return False

    self.data[symbol].dropna(inplace=True)

    if self.data[symbol].empty:
      return False

    if len(self.data[symbol]) < self.needed_periods:
      return False

    return True

  def check_status(self, typs, symbol):
    for typ in getattr(self, typs):
      if key(typ, 'symbol') == symbol and key(typ, 'qty') != 0:
        return True

    return False

  def get_qty(self, price):
    allocation = self.buying_power / self.max_positions

    if self.max_positions == len(self.positions):
      return 0

    return max(1, int(allocation / (price * 1.05)))

  def trade(self):
    for order in self.selector():
      if not self.allow_daytrading:
        print('   Placing a buy order for {} {}'.format(order['qty'], order['symbol']))
        self.apc.buy(order['symbol'], order['qty'])
        continue

      if self.allow_daytrading and self.stop_loss and self.take_profit:
        print('   Placing a bracket order for {} {}'.format(order['qty'], order['symbol']))
        self.apc.bracket_order(
          order['symbol'], order['qty'], order['price'] * self.take_profit,
          order['price'] * self.stop_loss, tif='gtc'
        )


  # Live monitoroing if allow_daytrading=False


  def sell(self, symbol):
    for position in self.positions:
      if position['symbol'] == symbol:
        self.apc.sell(symbol, position['qty'])
        self.streams.remove(f'T.{symbol}')

        print('   Placing a sell order for {} {}'.format(position['qty'], symbol))

        # Restart monitoring
        self.stream.close()
        self.stream = self.apc_stream.connect(self.streams, on_message=self.monitor_positions)
        self.positions = self.apc.get_positions()

  def live_monitoring(self):
    self.positions = self.apc.get_positions()
    self.streams = ['T.{}'.format(p['symbol']) for p in self.positions]

    print('      ~~Monitoring started...')
    print('      ~~Streams to monitor today: ', self.streams)
    self.stream = self.apc_stream.connect(self.streams, on_message=self.monitor_positions)

  def unwrap_message(self, message):
    message = json.loads(message)

    if 'data' not in message:
      return

    data = message['data']

    if 'T' not in data:
      return

    return (data['T'], data['p'])

  def monitor_positions(self, ws, message):
    symbol, price = self.unwrap_message(message)

    self.monitoring(symbol, price)