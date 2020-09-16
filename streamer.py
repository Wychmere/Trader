import sys
import config
import zmq_msg
import logging
import pathlib
import importlib
from alpaca_trade_api import StreamConn

WAIT_AFTER_ERROR = 3
STRATEGY_FILE_PREFIX = 'stock_'

def construct_logger(filename):
    log_headers = [logging.FileHandler(filename), logging.StreamHandler()]
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=log_headers)
    return logging.getLogger(__name__)

def construct_subscriptions(initial_subscriptions=[]):
    working_directory = pathlib.Path(__file__).parent
    strategy_files = working_directory.glob(f'{STRATEGY_FILE_PREFIX}*.py')
    for strategy_file in strategy_files:
        module_name = strategy_file.name.split('.py')[0]
        strategy = sys.modules.get(module_name)
        strategy = importlib.import_module(module_name)
        initial_subscriptions.append(f'alpacadatav1/T.{strategy.symbol}')
    return initial_subscriptions

if __name__ == '__main__':
    log = construct_logger('streamer.log')
    zmq = zmq_msg.Client()

    if config.use_sandbox:
        base_url = 'https://paper-api.alpaca.markets'
    else:
        base_url = 'https://api.alpaca.markets'

    conn = StreamConn(
        key_id=config.api_key,
        secret_key=config.api_secret,
        base_url=base_url)

    @conn.on(r'.*')
    async def on_price_update(conn, channel, data):
        if channel.startswith('T.'):
            print('{} {} {}'.format(data.timestamp, data.symbol, data.price))
            zmq.write(
                type='price',
                data={
                    'price': data.price,
                    'symbol': data.symbol
                }
            )
        elif channel == 'trade_updates':
            zmq.write(type='order', data=data.order)

    subscriptions = construct_subscriptions(['trade_updates'])
    conn.run(subscriptions)
