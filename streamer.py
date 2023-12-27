import sys
import config
import zmq_msg
import logging
import pathlib
import importlib
from datetime import datetime
from alpaca_trade_api.common import URL
from alpaca_trade_api.stream import Stream


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

def construct_quote_subscriptions():
    working_directory = pathlib.Path(__file__).parent
    strategy_files = working_directory.glob(f'{STRATEGY_FILE_PREFIX}*.py')
    initial_subscriptions = []
    for strategy_file in strategy_files:
        module_name = strategy_file.name.split('.py')[0]
        strategy = sys.modules.get(module_name)
        strategy = importlib.import_module(module_name)
        initial_subscriptions.append(strategy.symbol)
    return initial_subscriptions

def valid_quote_conditions(conditions):
    for condition in (' ', 'I', '@'):
        if condition in conditions:
            return True
    return False

if __name__ == '__main__':
    log = construct_logger('streamer.log')
    zmq = zmq_msg.Client()

    if config.use_sandbox:
        base_url = 'https://paper-api.alpaca.markets'
        data_feed = 'iex'
    else:
        base_url = 'https://api.alpaca.markets'
        data_feed = 'sip'

    stream = Stream(
        key_id=config.api_key,
        secret_key=config.api_secret,
        base_url=URL(base_url),
        data_feed=data_feed
    )

    async def quote_callback(quote):
        if quote.tape not in (' ', 'B', 'C'):
            return
        if not valid_quote_conditions(quote.conditions):
            return
        zmq.write(
            type='price',
            data={
                'timestamp': datetime.now().isoformat(),
                'quote_timestamp': str(quote.timestamp),
                'price': quote.price,
                'symbol': quote.symbol
            }
        )

    async def trade_callback(trade):
        print(trade)
        zmq.write(type='order', data=dict(trade.order))

    symbols = construct_quote_subscriptions()
    stream.subscribe_trades(quote_callback, *symbols)
    stream.subscribe_trade_updates(trade_callback)
    stream.run()
