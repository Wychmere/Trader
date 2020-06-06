'''
This script imports the configuration and strategy modules
and runs the trading system.
It will scan the working directory for Python scripts with
names starting with STRATEGY_FILE_PREFIX and will consider
each one of the found files to be a separate strategy.
All strategies will be started in parallel (using Threads)
and the main process will be kept alive until all Trader
threads are terminated.
'''

import time
import config
import pathlib
import logging
import importlib
import trader as tr
from threading import Thread

# The strategy filename prefix is used for detecting multiple strategy files.
STRATEGY_FILE_PREFIX = 'stock_'

# The interval in seconds between starting Traders.
TRADERS_START_INTERVAL = 2


def construct_logger(name, log_file, level):
        '''
        Create logger object.

        Arguments:
        name (str): The name of the logger.
        log_file (str): The name of the log file to be generated.
        level (str): The log level, e.g. DEBUG, INFO, ERROR..

        Returns: logger
        '''

        logger = logging.getLogger(name)
        log_level = getattr(logging, level)
        logger.setLevel(log_level)

        log_format = '%(asctime)s [%(name)s] [%(levelname)s] %(message)s'
        formatter = logging.Formatter(log_format)

        # Add the console handler.
        if config.console_log:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        # Add the file handler.
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger


def construct_trader(strategy_file, config):
    '''
    Creates a trader dict.

    Arguments:
    strategy_file (str): The name of the strategy file.
    config (module): The config module.

    Returns:
    {
        'name': strategy name,
        'trader': Trader,
        'thread': Thread
    }
    '''
    # Load the strategy module.
    module_name = strategy_file.name.rstrip('.py')
    strategy_module = importlib.import_module(module_name)

    # Create a Trader.
    _trader = tr.Trader(
        api_key=config.api_key,
        api_secret=config.api_secret,
        config=config,
        strategy=strategy_module)

    # Create thread to run the Trader on.
    _thread = Thread(target=_trader.run_forever, daemon=True)

    # Rename the thread so we can use it's name for logging.
    _thread.name = module_name

    return {'name': module_name, 'trader': _trader, 'thread': _thread}


def main():
    # Create the main threads logger.
    log = construct_logger('main', config.log_file, config.log_level)

    # Find all strategy files and create a Trader for each file.
    traders = []
    working_directory = pathlib.Path(__file__).parent
    strategy_files = working_directory.glob(f'{STRATEGY_FILE_PREFIX}*.py')

    for strategy_file in strategy_files:
        traders.append(construct_trader(strategy_file, config))

    # Start traders one by one with interval between stars to avoid API overload.
    for trader in traders:
        log.info('Starting {}'.format(trader['name']))
        trader['thread'].start()
        time.sleep(TRADERS_START_INTERVAL)

    # Each 30 seconds check if there are alive Threads.
    # Threads can be terminated by the Trader raising SystemExit.
    while True:
        if any([t['thread'].is_alive() for t in traders]):
            time.sleep(30)
            continue
        else:
            log.info('All threads are terminated.')
            break


if __name__ == '__main__':
    main()
