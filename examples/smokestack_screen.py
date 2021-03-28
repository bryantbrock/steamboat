from ..alpaca_modules.alpaca_indicators import *
from ..alpaca_screen import AlpacaScreen
from dotenv import dotenv_values


class Screener(AlpacaScreen):
  max_price = 5
  min_price = 1
  high_low_avg = 10
  minimum_vol = 0.10
  short_sma = 20
  long_sma = 200
  atr_sma = 10
  atr = 14
  res = []

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
    high_volatility = self.data[symbol]['{}_atr'.format(self.atr_sma)].iloc[-1] > self.minimum_vol
    short_is_above = self.data[symbol]['is_above'].iloc[-1]

    price_week_ago = self.data[symbol]['close'].iloc[-5]
    pct_change = round(((price / price_week_ago) - 1) * 100, 2)
    dropped_enough = pct_change <= -15.00

    avg_pct_change = self.data[symbol][f'{self.high_low_avg}_high_low'].iloc[-1] * 100

    if high_volatility and short_is_above and dropped_enough:
      self.res.append({
        'symbol': symbol,
        'vol': self.data[symbol]['{}_atr'.format(self.atr_sma)].iloc[-1],
        'price': price,
        'pct_change': avg_pct_change,
      })



if __name__ == '__main__':

  config = dotenv_values('.env')

  algo = Screener(
    config['APC_API_KEY'],
    config['APC_SECRET_KEY'],
    paper=True,
    data_limit=600
  )

  algo.run()


  # Logging

  print('\n')

  sorted_data = sorted(algo.res, key=lambda x: x['vol'])
  sorted_data.reverse()

  for data in sorted_data:
    print(
      '{}: is priced at {} with volatility of {} and HL avg of {}'.format(
        data['symbol'], data['price'], data['vol'], data['pct_change']
      )
    )

  print('\n')
