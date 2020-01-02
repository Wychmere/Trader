'''
Stock trading module based on the Alpaca API.
Docs:
https://docs.alpaca.markets/api-documentation/api-v2/
https://github.com/alpacahq/alpaca-trade-api-python
'''
import time
import uuid
import config
import logging
import strategy
import traceback
import email_sender
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

        # The strategy and config modules will be always available.
        self.strategy = strategy
        self.config = config

        # Make sure that the strategy is safe.
        self._make_strategy_safe()

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

        # Setup email sending.
        if config.enable_email_monitoring:
            # Set the last_email_timestamp to current time.
            self.last_email_timestamp = time.time()
            self.email_sender = email_sender.EmailSender(config.sendgrid_api_key)

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
            position = self.client.get_position(self.symbol)
            self.log.debug('Fetched position: {}'.format(position._raw))
            return position._raw
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
        clock = self.client.get_clock()
        return clock._raw

    def run_forever(self):
        '''
        Handles all errors except KeyboardInterrupt.
        '''

        # Report if the market is open or closed.
        market_state = 'open' if self.get_clock()['is_open'] else 'closed'
        self.log.info('Starting Trader. The market is {}.'.format(market_state))

        # Run forever.
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

    def get_orders(self, status='all'):
        '''
        Get a list of all orders.

        Arguments:
        status (str) : open, closed or all

        Returns: Dict
        '''
        orders = self.client.list_orders(status=status)
        self.log.debug('Fetched orders: {}'.format(orders))
        return orders

    def get_account(self):
        '''
        Get the account information.
        Example:
        {
        "asset_id": "904837e3-3b76-47ec-b432-046db621571b",
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "asset_class": "us_equity",
        "avg_entry_price": "100.0",
        "qty": "5",
        "side": "long",
        "market_value": "600.0",
        "cost_basis": "500.0",
        "unrealized_pl": "100.0",
        "unrealized_plpc": "0.20",
        "unrealized_intraday_pl": "10.0",
        "unrealized_intraday_plpc": "0.0084",
        "current_price": "120.0",
        "lastday_price": "119.0",
        "change_today": "0.0084"
        }
        '''
        account = self.client.get_account()
        self.log.debug('Fetched account: {}'.format(account._raw))
        return account._raw

    def _loop(self):
        '''
        The main loop of Trader. Implement all trading logic here.
        '''
        # Executed only at the initial run.
        if not self.state:
            # The side map will be used for order side switching.
            self.state['side_map'] = {'buy': 'sell', 'sell': 'buy'}
            first_order_side = self.strategy.first_order_side

            # Check which set of order prices we should use.
            if first_order_side == 'buy':
                limit_price = self.strategy.initial_buy_limit_price
                stop_price = self.strategy.initial_buy_stop_price
            elif first_order_side == 'sell':
                limit_price = self.strategy.initial_sell_limit_price
                stop_price = self.strategy.initial_sell_stop_price

            # Generate the order parameters.
            order_parameters = {
                'symbol': self.symbol,
                'qty': self.strategy.quantity,
                'side': first_order_side,
                'type': self.strategy.initial_order_type,
                'time_in_force': self.strategy.time_in_force,
                'limit_price': limit_price,
                'stop_price': stop_price,
                'client_order_id' : self._generate_order_id('initial')}

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

            # Send email if monitoring is enabled.
            if self.config.enable_email_monitoring:
                self._send_status_email(last_order)

            # If the order is filled we will place new one.
            if last_order['status'] == 'filled':
                # Log the order data.
                self._log_order_status(last_order)

                # Check which set of order prices we should use.
                if self.state['next_order_side'] == 'buy':
                    limit_price = self.strategy.loop_buy_limit_price
                    stop_price = self.strategy.loop_buy_stop_price
                elif self.state['next_order_side'] == 'sell':
                    limit_price = self.strategy.loop_sell_limit_price
                    stop_price = self.strategy.loop_sell_stop_price

                # Generate the order parameters.
                order_parameters = {
                    'symbol': self.symbol,
                    'qty': self.strategy.quantity,
                    'side': self.state['next_order_side'],
                    'type': self.strategy.loop_order_type,
                    'time_in_force': self.strategy.time_in_force,
                    'limit_price': limit_price,
                    'stop_price': stop_price,
                    'client_order_id' : self._generate_order_id('loop')}

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
        initial_trade_price = self.strategy.initial_trade_price
        initial_limit_spread = self.strategy.initial_limit_spread
        loop_signal_price = self.strategy.loop_signal_price
        loop_trade_spread = self.strategy.loop_trade_spread
        loop_limit_spread = self.strategy.loop_limit_spread

        # We can't have market loop orders.
        assert self.strategy.loop_order_type != 'market'

        # Generate explicit order prices from the prices in the strategy.
        if self.strategy.initial_order_type == 'market':
            self.strategy.initial_buy_limit_price = None
            self.strategy.initial_buy_stop_price = None
            self.strategy.initial_sell_limit_price = None
            self.strategy.initial_sell_stop_price = None

        if self.strategy.initial_order_type == 'limit':
            self.strategy.initial_buy_limit_price = initial_trade_price
            self.strategy.initial_sell_limit_price = initial_trade_price
            self.strategy.initial_buy_stop_price = None
            self.strategy.initial_sell_stop_price = None

        if self.strategy.loop_order_type == 'limit':
            self.strategy.loop_buy_limit_price = loop_signal_price + loop_trade_spread + loop_limit_spread
            self.strategy.loop_sell_limit_price = loop_signal_price - loop_trade_spread - loop_limit_spread
            self.strategy.loop_buy_stop_price = None
            self.strategy.loop_sell_stop_price = None

        if self.strategy.initial_order_type == 'stop':
            self.strategy.initial_buy_limit_price = None
            self.strategy.initial_sell_limit_price = None
            self.strategy.initial_buy_stop_price = initial_trade_price
            self.strategy.initial_sell_stop_price = initial_trade_price

        if self.strategy.loop_order_type == 'stop':
            self.strategy.loop_buy_limit_price = None
            self.strategy.loop_sell_limit_price = None
            self.strategy.loop_buy_stop_price = loop_signal_price + loop_trade_spread
            self.strategy.loop_sell_stop_price = loop_signal_price - loop_trade_spread

        if self.strategy.initial_order_type == 'stop_limit':
            self.strategy.initial_buy_limit_price = initial_trade_price
            self.strategy.initial_sell_limit_price = initial_trade_price
            self.strategy.initial_buy_stop_price = initial_limit_spread
            self.strategy.initial_sell_stop_price = initial_limit_spread

        if self.strategy.loop_order_type == 'stop_limit':
            self.strategy.loop_buy_limit_price = loop_signal_price + loop_trade_spread
            self.strategy.loop_sell_limit_price = loop_signal_price - loop_trade_spread
            self.strategy.loop_buy_stop_price = loop_signal_price + loop_limit_spread
            self.strategy.loop_sell_stop_price = loop_signal_price - loop_limit_spread

    def _generate_order_id(self, prefix):
        '''
        Generate unique client order name. The max length of client order id is 48.
        '''
        order_id = '{}-{}'.format(prefix, uuid.uuid4().hex)
        return order_id[:48]

    def _log_order_status(self, order):
        '''
        Log data about given order.
        Note: This method relies on the client order id being prefixed by
        either "initial" or "loop", otherwise it will log the order type as
        "general" which should be avoided as it will make the log less helpful.
        '''
        if 'initial' in order['client_order_id']:
            order_type = 'initial'
        elif 'loop' in order['client_order_id']:
            order_type = 'loop'
        else:
            order_type = 'general'

        self.log.info(
            'The last {} {} order was filled at: {}'.format(
            order_type,
            order['side'],
            order['filled_avg_price']))

    def _send_status_email(self, order):
        '''
        Compare the timestamp of the last send email and it is more than
        the desired frequency send new email.
        '''

        # The time difference is current time minus last email time in seconds.
        time_diff = time.time() - self.last_email_timestamp

        # We need to convert the email frequency to monutes by multiplying it with
        # 60 because the time difference we are going to compare it with is in seconds
        # while the email_monitoring_frequency is intended to represent minutes.
        email_frequency_in_minutes = self.config.email_monitoring_frequency * 1

        if time_diff >= email_frequency_in_minutes:
            subject = 'Trader status update.'

            message = '''
            Current active order:<br>
            Symbol: {symbol}<br>
            Type: {type}<br>
            Side: {side}<br>
            Quantity: {quantity}<br>
            Created at: {created_at}<br>
            Status: {status}<br>
            Filled at: {filled_at}<br>
            <br>
            Number of open orders: {open_orders}<br>
            <br>
            Position size: {position}<br>
            Balance: {balance}<br>
            '''

            position = self.get_position()
            account = self.get_account()
            open_orders = self.get_orders(status='open')

            # Add variables to the message template.
            message = message.format(
                symbol=order['symbol'],
                type=order['type'],
                side=order['side'],
                quantity=order['qty'],
                created_at=order['created_at'],
                status=order['status'],
                filled_at=order['filled_at'],
                open_orders=len(open_orders),
                position=position,
                balance=account['cash'])

            # Send the email.
            self.email_sender.send(
                from_email=self.config.email_monitoring_sending_email,
                to_email=self.config.email_monitoring_receiving_email,
                subject=subject,
                message=message)

            # Update the last email timestamp.
            self.last_email_timestamp = time.time()
