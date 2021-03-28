

def MACD(data, fast=12, slow=26, ema=9):
  """
  Advanced moving average indicator.
  """
  for df in data:
    data[df]['ma_fast'] = data[df]['close'].ewm(span=fast, min_periods=fast).mean()
    data[df]['ma_slow'] = data[df]['close'].ewm(span=slow, min_periods=slow).mean()
    data[df]['macd'] = data[df]['ma_fast'] - data[df]['ma_slow']
    data[df]['signal'] = data[df]['macd'].ewm(span=ema, min_periods=ema).mean()

    # Drop columns
    data[df].drop(['ma_fast', 'ma_slow'], axis=1, inplace=True)

  return data


def stochastic(data, lookback=14, k=3, d=3):
  """
  Range from 0 - 100: closer to 100 shows it
  is reaching the end of it's trend
  """

  for df in data:
    data[df]['HH'] = data[df]['high'].rolling(lookback).max()
    data[df]['LL'] = data[df]['low'].rolling(lookback).min()
    data[df]['%K'] = (
      100 * (
        (
          data[df]['close'] - data[df]['LL']
        ) / (
          data[df]['HH'] - data[df]['LL']
        )
      )
    ).rolling(k).mean()

    data[df]['%D'] = data[df]['%K'].rolling(d).mean()

  return data


def ATR(data, periods=14):
  for df in data:
    data[df]['H-L'] = data[df]['high'] - data[df]['low']
    data[df]['H-PC'] = abs(data[df]['high'] - data[df]['close'].shift(1))
    data[df]['L-PC'] = abs(data[df]['low'] - data[df]['close'].shift(1))
    data[df]['TR'] = data[df][['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    data[df]['ATR'] = data[df]['TR'].ewm(span=periods, min_periods=periods).mean()

    data[df].drop(['H-L', 'H-PC', 'L-PC', 'TR'], axis=1, inplace=True)

  return data


def sma(data, col, periods=14):
  for df in data:
    data[df]['{}_{}'.format(periods, col.lower())] = data[df][col].rolling(periods).mean()

  return data

def is_above(data, sma1, sma2):
  for df in data:
    data[df]['is_above'] = data[df][f'{sma1}_close'] > data[df][f'{sma2}_close']

  return data

def high_low(data):
  for df in data:
    data[df]['high_low'] = (data[df]['high'] / data[df]['low']) - 1

  return data


def bollinger_bands(data, period=20):
  for df in data:
    data[df]['MB'] = data[df]['close'].rolling(period).mean()
    data[df]['UB'] = data[df]['MB'] + 2 * data[df]['close'].rolling(period).std(ddof=0)
    data[df]['LB'] = data[df]['MB'] - 2 * data[df]['close'].rolling(period).std(ddof=0)
    data[df]['BB_width'] = data[df]['UB'] - data[df]['LB']

    data[df].drop(['MB', 'UB', 'LB'], axis=1, inplace=True)

  return data
