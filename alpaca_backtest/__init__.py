from ..alpaca_modules.alpaca_api import Alpaca, get_symbols
import json
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import numpy as np



class AlpacaBacktest(object):

  def __init__(self, api_key, secret_key, min_price=1, max_price=100,
               data_limit=1000, periods='5Min', take_profit=1.10,
               stop_loss=0.97, stock_count=None):

    self.apc = Alpaca(api_key, secret_key)
    self.stock_count = stock_count
    self.stop_loss = stop_loss
    self.take_profit = take_profit
    self.periods = periods
    self.data_limit = data_limit
    self.max_price = max_price
    self.min_price = min_price

    self.position = {}
    self.trade_periods = {}
    self.trade_count = {}
    self.trade_return = {}
    self.trade_data = {}


  # Backtesting

  def run(self):
    self.symbols = [tick['symbol'] for tick in get_symbols(screener=self.stock_screen)][:self.stock_count]
    self.data = self.apc.historical_data(self.symbols, tf=self.periods, limit=self.data_limit)
    self.indicators()
    self.idxs = len(self.data[self.symbols[0]].index)
    self.data_since = self.data[self.symbols[0]].index[0]

    print('Data since ', self.data_since)
    print('Running backtest...')

    for symbol in self.symbols:
      if not self.check_data(symbol):
        continue

      self.symbol = symbol
      self.initialize_vars()

      for idx in range(1, len(self.data[symbol])-1):
        self.idx = idx
        self.same_period = False

        price_open = self.data[symbol]['open'][idx]
        price_close = self.data[symbol]['close'][idx]
        price_high = self.data[symbol]['high'][idx]
        price_low = self.data[symbol]['low'][idx]
        price_last = self.data[symbol]['close'][idx-1]

        if price_open == 0:
          self.add_return()
          continue

        if price_open < 1 or price_open > 5:
          self.add_return()
          continue

        if not self.position[symbol]:
          if self.analyze(symbol, price_open):
            self.buy()
            self.same_period = True

        if self.position[symbol]:
          self.increment_trade_periods()

          price_bought = self.price_bought()
          price_last = price_open if self.same_period else price_last

          tp_price = price_bought * self.take_profit
          sl_price = price_bought * self.stop_loss
          at_take_profit = tp_price <= price_high or tp_price <= price_close
          at_stop_loss = sl_price >= price_low or sl_price >= price_close

          if at_take_profit and at_stop_loss:

            # TODO: We are currently removing the trade
            # - rather, we should get 5 minute period
            # data for this specific day and determine
            # which one came first. Only applies if
            # our current periods are '1D' or '15Min'

            self.remove_trade_data()
            self.add_return()
            continue

          if at_stop_loss:
            self.sell('stop_loss', price_last)
            continue

          if at_take_profit:
            self.sell('take_profit', price_last)
            continue

          self.add_return((price_close / price_last) - 1)
          continue

        self.add_return()


      # Clean up
      self.add_return()

      if self.trade_count[symbol] != 0:
        if len(self.trade_data[symbol][self.trade_count[symbol]]) < 2:
          self.remove_trade_data()

      self.print_results()
      self.plot_daily_returns()


  # Utilities


  def check_data(self, symbol):
    if symbol not in self.data:
      return False

    self.data[symbol].dropna(inplace=True)

    if self.data[symbol].empty:
      return False

    if len(self.data[symbol]) < 5:
      return False

    return True

  def add_return(self, ret=0):
    self.trade_return[self.symbol].append(ret)

  def increment_trade_periods(self):
    self.trade_periods[self.symbol] += 1

  def remove_trade_data():
    print('Removing trade data.')
    self.position[self.symbol] = False
    self.trade_periods[self.symbol] = 0
    self.trade_data[self.symbol][self.trade_count[self.symbol]] = []

  def price_bought(self):
    self.trade_data[self.symbol][self.trade_count[self.symbol]][0]

  def initialize_vars(self):
    self.position[self.symbol] = False
    self.trade_periods[self.symbol] = 0
    self.trade_count[self.symbol] = 0
    self.trade_return[self.symbol] = [0]
    self.trade_data[self.symbol] = {1: []}

  def buy(self):
    price = self.data[self.symbol]['open'][self.idx]

    self.position[self.symbol] = True
    self.trade_count[self.symbol] += 1
    self.trade_periods[self.symbol] += 1
    self.trade_data[self.symbol][self.trade_count[self.symbol]] = [round(price * 1.005, 2)]

  def sell(self, typ, price_last):
    trade_list = self.trade_data[self.symbol][self.trade_count[self.symbol]]
    price = self.price_bought() * getattr(self, typ)

    trade_list.append(price * 0.995)
    trade_list.append(self.trade_periods[self.symbol])

    self.add_return((price * 0.995 / price_last) - 1)
    self.position[symbol] = False

  def indicator(self, func, *args, **kwargs):
    self.data = func(self.data, *args, **kwargs)


  # Logging


  def plot_daily_returns(self):
    daily_returns_df = pd.DataFrame()
    daily_returns_df['time'] = np.array(self.idxs)
    daily_returns_df.set_index('time', inplace=True)

    temp = pd.DataFrame()
    temp['time'] = np.array(self.idxs)
    temp.set_index('time', inplace=True)

    for symbol in self.symbols:
      if len(self.trade_return[symbol]) < self.idxs:
        continue

      temp[symbol] = np.array(
        self.trade_return[symbol][:self.idxs]
      )

    temp.replace(0, np.nan, inplace=True)
    daily_returns_df['strategy'] = np.cumsum(temp.mean(axis=1, skipna=True))

    plt.plot(
      daily_returns_df.index,
      daily_returns_df['strategy'],
    )

    plt.xlabel('time')
    plt.ylabel('return')
    plt.show()

  def print_results(self):
    success = 0
    failed = 0
    all_succ = []
    all_fail = []
    fail_days_in_trade = []
    succ_days_in_trade = []
    overall_return = [1]

    for symbol in self.symbols:
      for k, v in self.trade_data[symbol].items():
        if len(v) < 3:
          continue

        val = (v[1]/v[0])

        if val == 0:
          continue

        if val > 1:
          success += 1
          all_succ.append((v[1]/v[0]) - 1)
          succ_days_in_trade.append(v[2])

        if val < 1:
          failed += 1
          all_fail.append((v[1]/v[0]) - 1)
          fail_days_in_trade.append(v[2])

        overall_return.append(overall_return[-1] * val)

    if failed != 0:
      avg_failed = sum(i for i in all_fail) / max(1, len(all_fail))
      avg_failed_days = sum(i for i in fail_days_in_trade) / max(1, len(fail_days_in_trade))
      failed_results = {
        'failed_trades': failed,
        'avg_failed_trade': round(avg_failed, 2),
        'largest_failed_trade': round(min(all_fail), 2),
        'avg_time_in_failed_trade': round(avg_failed_days, 2),
        'longest_time_in_failed_trade': max(fail_days_in_trade),
      }
    else:
      failed_results = {}

    if success != 0:
      avg_success_days = sum(i for i in succ_days_in_trade) / max(1, len(succ_days_in_trade))
      avg_success = sum(i for i in all_succ) / max(1, len(all_succ))
      success_results = {
        'success_trades': success,
        'avg_success_trade': round(avg_success, 2),
        'largest_success_trade': round(max(all_succ), 2),
        'avg_time_in_success_trade': round(avg_success_days, 2),
        'longest_time_in_success_trade': max(succ_days_in_trade),
      }
    else:
      success_results = {}

    final = {}
    final.update(success_results)
    final.update(failed_results)
    final.update({
      'overall_return': round(overall_return[-1], 4),
      'data_since': str(self.data_since),
    })

    # Print results
    print(json.dumps(final, indent=4))
