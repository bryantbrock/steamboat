from datetime import datetime, timedelta, timezone

import time
import pytz
import requests


def is_dst(zonename):
  tz = pytz.timezone(zonename)
  now = pytz.utc.localize(datetime.utcnow())
  res = now.astimezone(tz).dst() != timedelta(0)

  return res


class AlpacaMarketTime(object):
  """
  This class sleeps unless the market is open.
  It is more accurate than running a cronjob as it
  watches for holidays and the like.

  However, the script is constanlty running meaning
  a pay-as-you-go model will cost more. I suggest using
  droplets from Digital Ocean to pay a flat fee, you
  can do so for as low as $5.
  """

  def __init__(self, api_key, secret_key):
    self.headers = {
      'APCA-API-KEY-ID': api_key,
      'APCA-API-SECRET-KEY': secret_key,
    }

  def get_clock(self):
    return requests.get(
      'https://api.alpaca.markets/v2/clock',
      headers=self.headers
    ).json()

  def get_sleep_seconds(self):
    market = self.get_clock()

    ny_next_open = datetime.fromisoformat(market['next_open'])
    ny_time_now = datetime.now(tz=pytz.timezone('US/Eastern'))

    utc_offset_local = -int(time.timezone / 3600.0)
    utc_offset_ny = -4 if is_dst('US/Eastern') else -5

    in_dl_time = time.localtime().tm_isdst == 1
    seconds = ny_next_open.timestamp() - ny_time_now.timestamp()

    open_date_ny = datetime.fromtimestamp(
      seconds + (ny_time_now + timedelta(hours=abs(utc_offset_local) + utc_offset_ny)).timestamp()
    ).strftime("%A, %B %d, %Y %I:%M:%S")

    open_date_local = datetime.fromtimestamp(
      seconds + ny_time_now.timestamp()
    ).strftime("%A, %B %d, %Y %I:%M:%S")

    print('Markets open on ', open_date_ny, f' :: NY Time (UTC {utc_offset_ny})')
    print('Markets open on ', open_date_local, f' :: Local Time (UTC {utc_offset_local})')

    return seconds

  def monitor(self, script):
    while True:
      market = self.get_clock()

      if market['is_open']:
        print('\n  => Markets are OPEN <=')
        script()

      print('\n  => Markets are CLOSED <=')

      seconds = self.get_sleep_seconds()

      time.sleep(seconds)
