from datetime import datetime, timedelta

import threading
import time
import pytz


def key(obj, k):
  return obj[k] if k in obj else None

def is_dst(zonename):
  tz = pytz.timezone(zonename)
  now = pytz.utc.localize(datetime.utcnow())

  return now.astimezone(tz).dst() != timedelta(0)

def get_time_till(market, till='next_open', log=True):
  nyc_then = datetime.fromisoformat(market[till])
  nyc_now = datetime.now(tz=pytz.timezone('US/Eastern'))

  local_offset = (
    (-int(time.timezone / 3600.0) + 1)
    if time.localtime().tm_isdst == 1 else
    -int(time.timezone / 3600.0)
  )
  ny_offset = -4 if is_dst('US/Eastern') else -5
  seconds = nyc_then.timestamp() - nyc_now.timestamp()

  ny_date = datetime.fromtimestamp(
          seconds + (nyc_now + timedelta(hours=abs(local_offset) + ny_offset)).timestamp()
  ).strftime("%A, %B %d, %Y %I:%M:%S")

  local_date = datetime.fromtimestamp(
          seconds + datetime.now().timestamp()
  ).strftime("%A, %B %d, %Y %I:%M:%S")

  open_close = till.split('_')[-1]

  if log:
    print(f'\n\n      _Markets {open_close} on ', ny_date, f' :: NY Time (UTC {ny_offset})')
    print(f'      _Markets {open_close} on ', local_date, f' :: Local Time (UTC {local_offset})')

  return seconds


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
      return self._stop_event.is_set()