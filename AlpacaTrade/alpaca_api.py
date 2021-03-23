from datetime import datetime, timedelta
from dateutil import tz

import pandas as pd
import websocket
import requests
import json
import time

"""

  This api client comes with two classes: `Alpaca` and `AlpacaStream`
  See https://github.com/bryantbrock/steamboat for more documentation.

"""



APC_DATA_ENDPOINT = 'https://data.alpaca.markets'
APC_ENDPOINT = 'https://api.alpaca.markets'
APC_PAPER_ENDPOINT = 'https://paper-api.alpaca.markets'


def pprint(data, indent=2):
  print(json.dumps(data, indent=indent))

def chunk(lst, n):
  return [lst[i:i + n] for i in range(0, len(lst), n)]


class Alpaca(object):

  def __init__(self, api_key, secret_key, paper=False, log=False):
    self.params = {}
    self.data = {}
    self.data_url = f'{APC_DATA_ENDPOINT}/v1'
    self.sandbox_url = f'{APC_PAPER_ENDPOINT}/v2'
    self.headers = {
      'APCA-API-KEY-ID': api_key,
      'APCA-API-SECRET-KEY': secret_key,
    }
    self.base_url = '{}/v2'.format(
      APC_PAPER_ENDPOINT if paper else APC_ENDPOINT
    )
    self.log = log

  def req(self, typ, endpoint, url='base_url'):
    try:
      res = getattr(requests, typ)(
        getattr(self, url) + endpoint,
        params=self.params,
        data=self.data,
        headers=self.headers
      )

      date = time.strftime('%Y-%m-%d %H:%M:%S')
      info = res.text[:90] + ('...' if len(str(res.text)) > 90 else ' ')

      if self.log:
        print('=> {} {} to {}: {}'.format(date, typ.upper(), endpoint, info))

      return res.json()
    except (Exception, ConnectionError) as err:
      print('Error making request: ', err)

  def close_positions(self, cancel_orders=None, symbol=None, qty=None):
    self.params = {'qty': qty} if symbol and qty else {'cancel_orders': cancel_orders}
    return self.req('delete', f'/positions/{symbol}' if symbol and qty else '/positions')

  def get_positions(self, symbol=None):
    return self.req('get', (f'/positions/{symbol}' if symbol else '/positions'))

  def get_account(self):
    return self.req('get', '/account')

  def get_orders(self, status="all"):
    self.params = {'status': status}
    return self.req('get', f'/orders')

  def cancel_orders(self, order_id=None):
    return self.req('delete', f'/orders/{order_id}' if order_id else '/orders')

  def update_order(self, qty, params):
    self.params = params
    return self.req('patch', '/orders')

  def order(self, side, symbol, quantity,
            typ='market', tif='day', limit_price=None,
            stop_price=None, trail_price=None, trail_percent=None):
    self.data = json.dumps({
      'symbol': symbol,
      'side': side,
      'qty': quantity,
      'type': typ,
      'time_in_force': tif
    })

    if typ == 'limit':
      self.data['limit_price'] = limit_price

    if typ == 'stop':
      self.data['stop_price'] = stop_price

    if typ == 'stop_limit':
      self.data['limit_price'] = limit_price
      self.data['stop_price'] = stop_price

    if typ == 'trailing_stop':
      self.data['trail_price'] = trail_price
      self.data['trail_percent'] = trail_percent

    return self.req('post', '/orders')

  def bracket_order(self, symbol, quantity, tplp, slsp, tif='day'):
    self.data = json.dumps({
      'symbol': symbol,
      'qty': quantity,
      'time_in_force': tif,
      'side': 'buy',
      'type': 'market',
      'order_class': 'bracket',
      'take_profit': {'limit_price': tplp},
      'stop_loss': {'limit_price': slsp, 'stop_price': slsp}
    })

    return self.req('post', '/orders')

  def buy(self, symbol, qty, tif="day"):
    return self.order('buy', symbol, qty, tif=tif)

  def sell(self, symbol, qty, tif="day"):
    return self.order('sell', symbol, qty, tif=tif)

  def stop_buy(self, symbol, qty, stop_price):
    return self.order('buy', symbol, qty, stop_price=stop_price, typ='stop')

  def stop_sell(self, symbol, qty, stop_price):
    return self.order('sell', symbol, qty, stop_price=stop_price, typ='stop')

  def trailing_stop_price(self, side, symbol, qty, stop_price):
      return self.order(side, symbol, qty, typ='trailing_stop', trail_price=stop_price)

  def trailing_stop_perc(self, side, symbol, qty, stop_perc):
      return self.order(side, symbol, qty, typ='trailing_stop', trail_percent=stop_perc)

  def get_bar_data(self, timeframe, params):
    self.params = params
    return self.req('get', f'/bars/{timeframe}', url='data_url')

  def get_last_trade(self, symbol):
    return self.req('get', f'/last/stocks/{symbol}', url='data_url')

  def get_clock(self):
    return self.req('get', '/clock')

  def historical_data(self, symbols, tf='1D',
                      limit=200, start='',
                      end='', after='', until=''):
    """
      Args: symbols (DataFrame column/list of symbols), tf, limit, start, end, after, until
      Returns: --> python object of key (symbol) and value (DataFrame of data)
    """
    data_headers = {
      't': 'time',
      'o': 'open',
      'h': 'high',
      'l': 'low',
      'c': 'close',
      'v': 'volume',
    }
    chunks = chunk(symbols, 200)
    symbol_chunks = []
    result = {}

    for section in chunks:
      symbol_chunks.append(','.join(section[i] for i in range(0, len(section))))

    for bite in symbol_chunks:
      params = {
        "symbols": bite,
        "limit": limit,
        "start": start,
        "end": end,
        "after": after,
        "until": until,
      }
      raw = self.get_bar_data(tf, params)

      for symbol, data in raw.items():
        if not data:
          continue

        result[symbol] = pd.DataFrame(data)
        result[symbol].rename(data_headers, axis=1, inplace=True)
        result[symbol]['time'] = pd.to_datetime(result[symbol]['time'], unit='s')
        result[symbol].set_index('time', inplace=True)

        # New York time
        index = result[symbol].index
        index = index.tz_localize('UTC').tz_convert('America/Indiana/Petersburg')

        # Non pre/post market data included
        result[symbol].between_time('09:31', '16:00')

    return result




class AlpacaStreaming(object):

  def __init__(self, api_key, secret_key):
    self.api_key = api_key
    self.secret_key = secret_key

  def authenticate(self, ws, streams):
    ws.send(json.dumps({
      'action': 'authenticate',
      'data': {
          'key_id': self.api_key,
          'secret_key': self.secret_key,
      }
    }))

    ws.send(json.dumps({
      'action': 'listen',
      'data': {'streams': streams}
    }))

  def connect(self, streams, on_message=None):
    ws = websocket.WebSocketApp(
      "wss://data.alpaca.markets/stream"
    )

    if on_message:
      ws.on_message = on_message

    def on_open(ws):
      return self.authenticate(ws, streams)

    ws.on_message = on_message if on_message else self.on_message
    ws.on_open = on_open
    ws.run_forever()

    return ws



# Custom function to grab all symbols
# ======



def get_symbols(limit=10000, exchanges=['nyse'],
                marketcap='small', screener=lambda x: True):

  """
    A simple request to the nasdaq site for all the stocks
    in the united states (region 'north_america').
  """

  params = []
  result = []
  agent = {
    'user-agent': 'Mozilla/5.0 (Macintosh; \
      Intel Mac OS X 11_2_2) AppleWebKit/537.36 \
      (KHTML,like Gecko) Chrome/88.0.4324.192 Safari/537.36',
  }

  for exchange in exchanges:
    params.append({'tableonly': False, 'limit': limit, 'exchange': exchange, 'marketcap': marketcap})

  for param in params:
    res = requests.get(
      'https://api.nasdaq.com/api/screener/stocks', headers=agent, params=param
    ).json()

    for ticker in res['data']['table']['rows']:
      # Fix small bug
      if ticker['pctchange'][-1] != '%':
        ticker['pctchange'] = '0.0%'

      ticker['symbol'] = ticker['symbol'].split(' ')[0]
      ticker['exchange'] = param['exchange']
      ticker['lastsale'] = float(ticker['lastsale'][1:])
      ticker['pctchange'] = float(ticker['pctchange'][:-2])/100

      passed = screener(ticker)

      if passed:
        result.append(ticker)


  return result
