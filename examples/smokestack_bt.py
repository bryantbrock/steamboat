from ..alpaca_modules.alpaca_indicators import *
from ..alpaca_backtest import AlpacaBacktest
from dotenv import dotenv_values

class Backtest(AlpacaBacktest):
  high_low_avg = 10
  minimum_vol = 0.10
  short_sma = 20
  long_sma = 200
  atr_sma = 10
  atr = 14

  def indicators(self):
    self.indicator(sma, 'close', periods=self.short_sma)
    self.indicator(sma, 'close', periods=self.long_sma)
    self.indicator(ATR, periods=self.atr)
    self.indicator(sma, 'ATR', periods=self.atr_sma)
    self.indicator(is_above, self.short_sma, self.long_sma)
    self.indicator(high_low)
    self.indicator(sma, 'high_low', periods=self.high_low_avg)

  def stock_screen(self, ticker):
    return ticker['lastsale'] < self.max_price and ticker['lastsale'] > self.min_price

  def analyze(self, symbol, price):
    price_week_ago = self.data[symbol]['close'][self.idx-5]
    pct_change = round(((price / price_week_ago) - 1) * 100, 2)

    dropped_enough = pct_change <= -15.00
    high_volatility = self.data[symbol]['{}_atr'.format(self.atr_sma)][self.idx] > self.minimum_vol
    short_is_above = self.data[symbol]['is_above'][self.idx]

    if dropped_enough and high_volatility and short_is_above:
      self.buy()



if __name__ == '__main__':

  config = dotenv_values('.env')

  bt = Backtest(
    config['APC_API_KEY'],
    config['APC_SECRET_KEY'],
    max_price=5,
    min_price=1,
    data_limit=400,
    stock_count=20
  )

  bt.run()