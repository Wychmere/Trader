import config
import zmq_msg
import logging
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

    @conn.on(r'^trade_updates$')
    async def on_account_updates(conn, channel, account):
        log.info(account.order)
        zmq.write(account.order)

    conn.run(['trade_updates'])
