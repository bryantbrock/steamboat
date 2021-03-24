from .alpaca_api import Alpaca, AlpacaStreaming


def live_monitoring(apc_trade):
  streams = []
  positions = []
  stream = None

  def monitor_positions(ws, message):
    message = json.loads(message)

    if 'data' not in message:
      return

    data = message['data']

    if 'T' not in data:
      return

    symbol = data['T']
    price = data['p']
    has_order = False

    for position in positions:
      if position['symbol'] == symbol:
        buy_price = float(position['avg_entry_price'])
        hit_take_profit = (apc_trade.take_profit * buy_price) <= price
        hit_stop_loss = (apc_trade.stop_loss * buy_price) >= price

        if hit_take_profit or hit_stop_loss:
          apc_trade.apc.sell(symbol, position['qty'])
          streams.remove(f'T.{symbol}')

          print('Placing a sell order for {} {}'.format(position['qty'], symbol))

          # Restart monitoring
          stream.close()
          stream.connect(streams, on_message=monitor_positions)


  positions = apc_trade.apc.get_positions()
  streams = ['T.{}'.format(s['symbol']) for s in positions]
  stream = apc_trade.apc_stream.connect(streams, on_message=monitor_positions)
