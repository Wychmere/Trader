'''
This script imports the configuration and strategy modules
and runs the trading system.
It will scan the working directory for Python scripts with
names starting with STRATEGY_FILE_PREFIX and will consider
each one of the found files to be a separate strategy.
All strategies will be started in parallel (using Threads)
and the main process will be kept alive until all Trader
threads are terminated.

By default the console output will show logs by the different
strategies that are running. To enter into user input mode press
ctrl+C and wait for the ">>>" prompt to show up.
Supported user commands:
kill <strategy name> - Terminates specific strategy e.g stock_1
kill all - Terminates all strategies.
'''

import time
import signal
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


class ServiceExit(Exception):
    '''
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    '''
    pass

def service_shutdown(signum, frame):
    raise ServiceExit

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
    # Load the strategy module. We know that it will be a filename
    # ending with ".py" so we can split it at this sequence and keep
    # the first part.
    module_name = strategy_file.name.split('.py')[0]
    strategy_module = importlib.import_module(module_name)

    # Create a Trader.
    _trader = tr.Trader(
        api_key=config.api_key,
        api_secret=config.api_secret,
        config=config,
        strategy=strategy_module)

    _trader.daemon = True

    # Create thread to run the Trader on.
    # _thread = Thread(target=_trader.run_forever, daemon=True)

    # Rename the thread so we can use it's name for logging.
    # _thread.name = module_name
    _trader.name = module_name

    #return {'name': module_name, 'trader': _trader, 'thread': _thread}
    #return {'name': module_name, 'trader': _trader}
    return _trader

def register_signals():
    '''
    Register the signals that are going to be
    send to Trader from main.
    '''
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)

def get_user_input():
    user_input = input('\n>>>')
    tokens = user_input.split(' ')
    keys = ('action', 'target')
    return {k: v for k, v in zip(keys, tokens)}

def main():
    register_signals()

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
        log.info('Starting {}'.format(trader.name))
        trader.start()
        time.sleep(TRADERS_START_INTERVAL)

    # Each 5 seconds check if there are alive Threads.
    # Threads can be terminated by the Trader raising SystemExit.
    while True:
        try:
            if not any([t.is_alive() for t in traders]):
                log.info('All threads are terminated.')
                break
            time.sleep(5)

        # ServiceExit will be raised on KeyboardInterrupt we will use this
        # as the user input terminal command.
        except ServiceExit:

            # Disable logging while in user input mode.
            for trader in traders:
                logger = logging.getLogger(trader.name)
                logger.disabled = True

            # Get user input.
            user_input = get_user_input()

            # Kill trades.
            for trader in traders:
                if user_input['action'] == 'kill':
                    if trader.name == user_input['target'] \
                    or user_input['target'] == 'all':
                        trader._shutdown_flag.set()

            # Enable logging.
            for trader in traders:
                logger = logging.getLogger(trader.name)
                logger.disabled = False

if __name__ == '__main__':
    main()
