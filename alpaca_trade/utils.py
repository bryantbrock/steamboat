from datetime import datetime, timedelta
import time
import pytz


def key(obj, k):
  return obj[k] if k in obj else None

def is_dst(zonename):
  tz = pytz.timezone(zonename)
  now = pytz.utc.localize(datetime.utcnow())

  return now.astimezone(tz).dst() != timedelta(0)

def get_time_till(market, till='next_open'):
  next_open = datetime.fromisoformat(market[till])
  nyc_time = datetime.now(tz=pytz.timezone('US/Eastern'))

  local_offset = (
    (-int(time.timezone / 3600.0) + 1)
    if time.localtime().tm_isdst == 1 else
    -int(time.timezone / 3600.0)
  )
  ny_offset = -4 if is_dst('US/Eastern') else -5
  seconds = next_open.timestamp() - nyc_time.timestamp()

  ny_open_date = datetime.fromtimestamp(
          seconds + (nyc_time + timedelta(hours=abs(local_offset) + ny_offset)).timestamp()
  ).strftime("%A, %B %d, %Y %I:%M:%S")

  local_open_date = datetime.fromtimestamp(
          seconds + nyc_time.timestamp()
  ).strftime("%A, %B %d, %Y %I:%M:%S")

  open_close = till.split('_')[-1]

  print(f'\n\n      _Markets {open_close} on ', ny_open_date, f' :: NY Time (UTC {ny_offset})')
  print(f'      _Markets {open_close} on ', local_open_date, f' :: Local Time (UTC {local_offset})')

  return seconds