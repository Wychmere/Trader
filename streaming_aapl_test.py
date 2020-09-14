import config
import sys
import logging
from datetime import datetime
from alpaca_trade_api import StreamConn

if config.use_sandbox:
    base_url = 'https://paper-api.alpaca.markets'
else:
    base_url = 'https://api.alpaca.markets'

conn = StreamConn(
    key_id=config.api_key,
    secret_key=config.api_secret,
    base_url=base_url)


def ts():
    return datetime.now()


def log(*args, **kwargs):
    print(ts(), " ", *args, **kwargs)


def debug(*args, **kwargs):
    print(ts(), " ", *args, file=sys.stderr, **kwargs)


def ms2date(ms, fmt='%Y-%m-%d'):
    if isinstance(ms, pd.Timestamp):
        return ms.strftime(fmt)
    else:
        return datetime.fromtimestamp(ms/1000).strftime(fmt)


async def on_tick(conn, channel, bar):
    try:
        percent = (bar.close - bar.dailyopen)/bar.close * 100
    except:  # noqa
        percent = 0

    print(f'{channel:<6s} {ms2date(bar.end)}  {bar.symbol:<10s} '
          f'{percent:>8.2f}% {bar.open:>8.2f} {bar.close:>8.2f} '
          f' {bar.volume:<10d}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # This is another way to setup wrappers for websocket callbacks, handy if conn is not global.
    on_tick = conn.on(r'A$')(on_tick)

    conn.run(['alpacadatav1/A.AAPL'])

