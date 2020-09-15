import config
import logging
from alpaca_trade_api import StreamConn

if config.use_sandbox:
    base_url = 'https://paper-api.alpaca.markets'
else:
    base_url = 'https://api.alpaca.markets'

conn = StreamConn(
    key_id=config.api_key,
    secret_key=config.api_secret,
    base_url=base_url)

async def on_data(conn, channel, data):
    if channel.startswith('T.'):
        print(data.price)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    on_data = conn.on(r'.*')(on_data)

    conn.run(['alpacadatav1/T.AAPL'])

