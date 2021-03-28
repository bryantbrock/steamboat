from ..alpaca_modules.alpaca_indicators import *
from ..alpaca_trade import AlpacaTrade
from dotenv import dotenv_values


class Smokestack(AlpacaTrade):
  short_sma = 20
  long_sma = 200
  atr = 14

  def indicators(self):
    self.indicator(SMA, periods=self.short_sma)
    self.indicator(SMA, periods=self.long_sma)
    self.indicator(ATR, periods=self.atr)

  def screener(self, ticker_data):
    return ticker_data['lastsale'] < 5 and ticker_data['lastsale'] > 1

  def analyzer(self, symbol, price):
    price_week_ago = self.data[symbol]['{}_sma'.format(self.short_sma)].iloc[-5]
    pct_change = round(((price / price_week_ago) - 1) * 100, 2)

    dropped_enough = pct_change <= -15.00
    short_is_above = \
      self.data[symbol]['{}_sma'.format(self.short_sma)].iloc[-1] > \
      self.data[symbol]['{}_sma'.format(self.long_sma)].iloc[-1]

    if dropped_enough and short_is_above:
      print(f'   {symbol} Passed! {pct_change}% change and 20sma is above 200sma')

    return dropped_enough and short_is_above

  def selector(self):
    for order in self.pending_orders:
      order['volatility'] = sum(self.data[order['symbol']]['ATR'].iloc[-10:]) / 10

    return sorted(self.pending_orders, key=lambda x: x['volatility'])[:self.max_positions]

  def monitoring(self, symbol, price):
    for position in self.positions:
      if position['symbol'] == symbol:
        buy_price = float(position['avg_entry_price'])
        hit_take_profit = (self.take_profit * buy_price) <= price
        hit_stop_loss = (self.stop_loss * buy_price) >= price

        if hit_take_profit or hit_stop_loss:
          self.sell(symbol)



if __name__ == '__main__':

  config = dotenv_values('.env')

  strategy = Smokestack(
    config['APC_API_KEY'],
    config['APC_SECRET_KEY'],
    paper=True,
    max_positions=1,
    data_limit=400,
    stop_loss=0.97,
    take_profit=1.15
  )

  strategy.run(account=config['ACCOUNT'])
