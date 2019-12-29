'''
Stock trading module based on the Alpaca API.
Docs:
https://docs.alpaca.markets/api-documentation/api-v2/
https://github.com/alpacahq/alpaca-trade-api-python
'''
import time
import config
import logging
import strategy
import traceback
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError as APIError

class Trader:
    '''
    The trander handles communication with the Alpaca API.

    Arguments:
    api_key (str) : The api key.
    api_secret (str) : The api secret.
    config (module) : The config module.
    strategy (module) : The strategy module.
    '''
    def __init__(self, api_key, api_secret, config, strategy):
        # All state related variables will be tracked in the state dict.
        # Don't initiate any keys here because the _loop function detects if
        # it is running for the first time by checking its truth value.
        self.state = {}

        # The strategy module will be always available.
        self.strategy = strategy

        # Trader supports single symbol at this point.
        self.symbol = self.strategy.symbol

        self.update_time = config.update_time
        self.sleep_after_error = config.sleep_after_error

        # Set the base url.
        if config.use_sandbox:
            base_url = 'https://paper-api.alpaca.markets'
        else:
            base_url = 'https://api.alpaca.markets'

        # Create the Alpaca API client.
        self.client = tradeapi.REST(
            key_id=api_key,
            secret_key=api_secret,
            base_url=base_url,
            api_version='v2')

        # Setup logging.
        self.set_logger(
            level=config.log_level,
            console_log=config.console_log,
            log_file=config.log_file)

    def set_logger(self, level, console_log, log_file):
        '''
        Setup the logging.

        Arguments:
        level (str) : The log level: DEBUG, INFO, WARNING, INFO
        console_log (str) : If true logs will be printed to the console.
        log_file (str) : The filename of the log file to be generated.
        '''
        log_headers = [logging.FileHandler(log_file)]
        if console_log:
            log_headers.append(logging.StreamHandler())
        log_format = '%(asctime)s [%(levelname)s] %(message)s'
        logging.basicConfig(level=getattr(logging, level),
            format=log_format, handlers=log_headers)
        self.log = logging.getLogger()

    def get_position(self):
        '''
        Get the position for the symbol.
        If there is no position we will get APIError and will return None
        '''
        try:
            return self.client.get_position(self.symbol)
        except APIError:
            return None

    def get_clock(self):
        '''
        Get the Alpaca market clock.
        Returns (dict):
        {
            'is_open': False,
            'next_close': '2019-12-30T16:00:00-05:00',
            'next_open': '2019-12-30T09:30:00-05:00',
            'timestamp': '2019-12-28T19:48:41.067338957-05:00'
        }
        '''
        return self.client.get_clock()

    def run_forever(self):
        '''
        Handle all errors.
        '''
        # Make sure that we have a strategy to execute.
        assert self.strategy

        while True:
            try:
                self._loop()
                time.sleep(self.update_time)
            # Kayboard interupts can terminate the run.
            except KeyboardInterrupt:
                self.log.info('Canceling all orders and terminating.')
                self.client.cancel_all_orders()
                return 0
            # Any other error will be ignored.
            except:
                self.log.warning('The main loop failed. {}'.format(
                    traceback.format_exc()))
                time.sleep(self.sleep_after_error)

    def submit_order(self, parameters):
        '''
        Submit an order to the exchange.

        Arguments:
        parameters (dict) : Contains all the parameters accepted by the /orders

        Docs:
        https://docs.alpaca.markets/api-documentation/api-v2/orders/

        Returns: Dict
        '''
        order = self.client.submit_order(**parameters)
        self.log.debug('Created order: {}'.format(order._raw))
        return order._raw

    def get_order(self, order_id):
        '''
        Get an order by its ID.

        Arguments:
        order_id (str) : The order id.

        Returns: Dict
        '''
        order = self.client.get_order(order_id)
        self.log.debug('Fetched order: {}'.format(order._raw))
        return order._raw

    def _loop(self):
        '''
        The main loop of Trader. Implement all trading logic here.
        '''
        # Executed only at the initial run.
        if not self.state:
            # Make sure that the strategy is safe.
            self._make_strategy_safe()

            # The side map will be used for order side switching.
            self.state['side_map'] = {'buy': 'sell', 'sell': 'buy'}
            first_order_side = self.strategy.first_order_side

            # Check which set of order prices we should use.
            if first_order_side == 'buy':
                limit_price = self.strategy.buy_limit_price
                stop_price = self.strategy.buy_stop_price
            elif first_order_side == 'sell':
                limit_price = self.strategy.sell_limit_price
                stop_price = self.strategy.sell_stop_price

            # Generate the order parameters.
            order_parameters = {
                'symbol': self.symbol,
                'qty': self.strategy.quantity,
                'side': first_order_side,
                'type': self.strategy.first_order_type,
                'time_in_force': self.strategy.time_in_force,
                'limit_price': limit_price,
                'stop_price': stop_price}

            # Create the first order.
            self.log.info('Creating the first order: {}'.format(order_parameters))
            order = self.submit_order(order_parameters)

            # Keep track of the order id and next order side.
            self.state['last_order_id'] = order['id']
            self.state['next_order_side'] = self.state['side_map'][first_order_side]

        # Executed on each update after the initial run.
        else:
            # Get the order data of the last order.
            last_order_id = self.state['last_order_id']
            last_order = self.get_order(last_order_id)

            # If the order is filled we will place new one.
            if last_order['status'] == 'filled':
                self.log.info('The last order was filled.')

                # Check which set of order prices we should use.
                if self.state['next_order_side'] == 'buy':
                    limit_price = self.strategy.buy_limit_price
                    stop_price = self.strategy.buy_stop_price
                elif self.state['next_order_side'] == 'sell':
                    limit_price = self.strategy.sell_limit_price
                    stop_price = self.strategy.sell_stop_price

                # Generate the order parameters.
                order_parameters = {
                    'symbol': self.symbol,
                    'qty': self.strategy.quantity,
                    'side': self.state['next_order_side'],
                    'type': self.strategy.first_order_type,
                    'time_in_force': self.strategy.time_in_force,
                    'limit_price': limit_price,
                    'stop_price': stop_price}

                # Create the order.
                self.log.info('Creating order: {}'.format(order_parameters))
                order = self.submit_order(order_parameters)

                # Keep track of the order id and next order side.
                self.state['last_order_id'] = order['id']
                self.state['next_order_side'] = self.state['side_map'][self.state['next_order_side']]

    def _make_strategy_safe(self):
        '''
        Check the set of parameters in the strategy and make sure
        that unneeded ones are set to None and needed ones are not.
        '''
        # For market orders we don't need any price parameters.
        if self.strategy.first_order_type == 'market':
            self.strategy.buy_limit_price = None
            self.strategy.buy_stop_price = None
            self.strategy.sell_limit_price = None
            self.strategy.sell_stop_price = None
        # For limit orders we need limit prices but not stop prices.
        elif self.strategy.first_order_type == 'limit':
            assert self.strategy.buy_limit_price
            assert self.strategy.sell_limit_price
            self.strategy.buy_stop_price = None
            self.strategy.sell_stop_price = None
        # For stop orders we only need stop prices.
        elif self.strategy.first_order_type == 'stop':
            assert self.strategy.buy_stop_price
            assert self.strategy.sell_stop_price
            self.strategy.buy_limit_price = None
            self.strategy.sell_limit_price = None
        # For stop limit orders we need all prices.
        elif self.strategy.first_order_type == 'stop_limit':
            assert self.strategy.buy_limit_price
            assert self.strategy.sell_limit_price
            assert self.strategy.buy_stop_price
            assert self.strategy.sell_stop_price

# TODO: Remove after testing.
if __name__ == '__main__':
    tr = Trader(
        api_key=config.api_key,
        api_secret=config.api_secret,
        config=config,
        strategy=strategy)

    tr.run_forever()
