'''
Stock trading module based on the Alpaca API.
Docs:
https://docs.alpaca.markets/api-documentation/api-v2/
https://github.com/alpacahq/alpaca-trade-api-python
'''
import time
import uuid
import signal
import zmq_msg
import logging
import traceback
import threading
import email_sender
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError as APIError
from alpaca_trade_api.entity import Order as alpaca_order


class OrderRejectedError(Exception):
    '''
    This exception is raised when order placing fails with APIError.
    '''
    pass


class Trader(threading.Thread):
    '''
    The trander handles communication with the Alpaca API.

    Arguments:
    api_key (str) : The api key.
    api_secret (str) : The api secret.
    config (module) : The config module.
    strategy (module) : The strategy module.
    '''
    def __init__(self, api_key, api_secret, config, strategy):
        # Trader is runnable as a thread so we need to set it up
        # accordingly. If it has to be terminated from the parrent
        # process it will receive a flag and will go trough it's
        # termination process including cancelling existing orders.
        threading.Thread.__init__(self)
        self._shutdown_flag = threading.Event()

        # All state related variables will be tracked in the state dict.
        # Don't initiate any keys here because the _loop function detects if
        # it is running for the first time by checking its truth value.
        self.state = {}

        # The strategy and config modules will be always available.
        self.strategy = strategy
        self.config = config

        # Make sure that the strategy is safe.
        # TODO: Remove if not needed.
        #self._make_strategy_safe()

        # Trader supports single symbol at this point.
        self.symbol = self.strategy.symbol

        self.update_time = self.config.update_time
        self.sleep_after_error = self.config.sleep_after_error

        # The number of retries if the order creation fails.
        self.retry_order_creation = self.config.retry_order_creation

        self.order_status_check_delay = self.config.order_status_check_delay

        # Set the base url.
        if self.config.use_sandbox:
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
        self.log = self.construct_logger()

        # Setup email sending.
        if strategy.enable_email_monitoring:
            # Set the last_email_timestamp to current time.
            self.last_email_timestamp = time.time()
            self.email_sender = email_sender.EmailSender(self.config.sendgrid_api_key)

        self.zmq_client = zmq_msg.Client()

        if self.strategy.initial_order_side == 'buy':
            self.order_sides = ['buy', 'sell']
        elif self.strategy.initial_order_side == 'sell':
            self.order_sides = ['sell', 'buy']

    def construct_logger(self):
        '''
        Create logger object.
        Returns: logger
        '''

        # The name is used to identify loogers and log files.
        # The log file will be named as strategy_name + config.log_file.
        name = self.strategy.__name__
        log_file = '{}_{}'.format(name, self.config.log_file)

        logger = logging.getLogger(name)
        logger.propagate = False
        log_level = getattr(logging, self.config.log_level)
        logger.setLevel(log_level)

        # Thread names match strategy names so we can use it in the formatting.
        log_format = '%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s'
        formatter = logging.Formatter(log_format)

        # Add the console handler.
        if not logger.handlers:
            if self.config.console_log:
                stream_handler = logging.StreamHandler()
                stream_handler.setFormatter(formatter)
                logger.addHandler(stream_handler)

            # Add the file handler.
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

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

    def run(self):
        #self.run_forever()
        ##################
        while True:
            try:
                self._signals()
                self.loop()
                time.sleep(self.update_time)
            except KeyboardInterrupt:
                self._terminate(reason='User interruption.')
            # Explicit system exit.
            except SystemExit:
                raise SystemExit
            # Any other error will be ignored.
            except:
                self.log.warning('The main loop failed. {}'.format(
                    traceback.format_exc()))
                time.sleep(self.sleep_after_error)

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
                self._signals()
                self._loop()
                time.sleep(self.update_time)
            # Creating of new order failed.
            except OrderRejectedError:
                if self.retry_order_creation > 0:
                    self.retry_order_creation -= 1
                    # By clearing the state dict we restart the strategy.
                    self.state = {}
                    self.log.warning(
                        'Order creation failed. Retying in {} seconds.'.format(
                            self.sleep_after_error))
                    time.sleep(self.sleep_after_error)
                else:
                    termination_reason = 'Max order creation retries reached.'
                    if self.strategy.enable_email_monitoring:
                        response = self._send_termination_alert(reason=termination_reason)
                        self.log.info(response)
                    self._terminate(reason=termination_reason)
            # Kayboard interupts can terminate the run.
            except KeyboardInterrupt:
                self._terminate(reason='User interruption.')
            # Explicit system exit.
            except SystemExit:
                raise SystemExit
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

        Returns: Dict on success and None on error.
        '''
        try:
            if self.strategy.order_instructions:
                order = self._submit_order_with_instructions(**parameters)
            else:
                order = self.client.submit_order(**parameters)
            #self.log.debug('Created order: {}'.format(order._raw))
            return order._raw
        except APIError as err:
            self.log.error('API error during order creation: {}'.format(err._error))
            return None

    def get_order(self, order_id, streaming=True):
        '''
        Get an order by its ID.

        Arguments:
        order_id (str) : The order id.

        Returns: Dict
        '''
        if streaming:
            response = self.zmq_client.read()
            order = response['orders'].get(order_id)
            self.log.debug('Fetched order: {}'.format(order))
            if not order:
                # New orders doesn't show in the streaming API
                # so we will assume that the order status is "new"
                return {'status': 'new', 'id': order_id}
            return order

        order = self.client.get_order(order_id)
        self.log.debug('Fetched order: {}'.format(order._raw))
        return order._raw

    def order_is_oco(self, order):
        return order.get('legs')

    def get_orders(self, status='all', streaming=True):
        '''
        Get a list of all orders.

        Arguments:
        status (str) : open, closed or all

        Returns: Dict
        '''

        if streaming:
            response = self.zmq_client.read()
            orders = response['orders']
            if not orders:
                return []
            orders = [o for o in orders.values() if o['status'] == status]
            self.log.debug('Fetched orders: {}'.format(orders))
            return orders

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

    def cancel_symbol_orders(self):
        '''
        Cancel all orders for the traded symbol.
        '''
        try:
            skip_statusses = ['canceled', 'filled']
            open_orders = self.get_orders(streaming=False)
            for order in open_orders:
                if order.symbol == self.symbol \
                and order.status not in skip_statusses:
                    self.client.cancel_order(order.id)
        except:
            err = traceback.format_exc()
            self.log.error(f'Canceling {self.symbol} orders failed: {err}')

    def oco_filled(self, order, leg):
        '''
        Checks if an order is OCO and if so - is the take profit leg filled.
        Arguments:
        order (dict) : The order dict.
        leg (str) : Which order to check. 'stop_loss' or 'take_profit'
        '''
        if not order.get('legs'):
            return False

        if leg == 'take_profit':
            if order['status'] == 'filled':
                return True

        if leg == 'stop_loss':
            if order['legs'][0]['status'] == 'filled':
                return True

        return False

    def _signals(self):
        '''
        Check signals and raise the corresponding exceptions.
        '''
        if self._shutdown_flag.is_set():
            raise KeyboardInterrupt

    def log_event(self, event_type, log_level='info', **kwargs):
        kw_data = ['{}={}'.format(k, v) for k, v in kwargs.items()]
        info = ' | '.join(kw_data)
        log_func = getattr(self.log, log_level)
        log_func('{}{}'.format(event_type, info))

    def switch_order_side(self):
        self.order_sides.reverse()
        return self.order_sides[0]

    def reverse_order_side(self):
        self.order_side()

    def order_parameters(self):
        return {
            'symbol': self.symbol,
            'qty': self.strategy.quantity,
            'side': self.state['side'],
            'type': 'market',
            'time_in_force': self.strategy.time_in_force,
            'client_order_id': self._generate_order_id('initial')
        }

    def wait_for_fill(self, order):
        fail_counter = 0
        filled = False
        status = 'Unknown'
        for _ in range(2):
            order = self.get_order(order['id'])
            if not order:
                if fail_counter < 3:
                    continue
                else:
                    break
            elif order['status'] in ('rejected', 'canceled',):
                status = order['status']
                break
            elif order['status'] == 'filled':
                status = order['status']
                filled = True
                break
            else:
                status = order['status']
            time.sleep(2)
        return filled, status, order

    def market_price(self, streaming=True):
        if streaming:
            response = self.zmq_client.read()
            price = response['prices'][self.symbol]['price']
            #timestamp = response['prices'][self.symbol]['timestamp']
            #timestamp = timestamp.split('.')[0]
            #self.log.info(
            #    f'Fetched price: {self.symbol} | {price} | {timestamp}')
            return price
        else:
            last_trade = self.client.get_last_trade(self.symbol)
            return last_trade.price

    def loop(self):
        '''The main loop of Trader. Implement all trading logic here.'''

        market_price = self.market_price()

        # Executed only at the initial run.
        if not self.state:
            self.state['side'] = self.strategy.initial_order_side
            self.state['price'] = self.strategy.initial_signal_price

            if self.state['side'] == 'buy' and market_price < self.state['price'] \
            or self.state['side'] == 'sell' and market_price > self.state['price']:
                return

            order_params = self.order_parameters()

            # Create the first order.
            order = self.submit_order(order_params)

            self.log.info('Created initial order: {}'.format(order_params))

            if not order:
                self.log.warning('Creating initial order failed.')
                self.cancel_symbol_orders()
                self.state = {}
                return

            filled, status, order = self.wait_for_fill(order)

            if not filled:
                self.log.warning('Initial order failed with status: {}'.format(status))
                self.cancel_symbol_orders()
                self.state = {}
                return

            self.log.info('Order filled.')
            self.state['last_order'] = order
            self.state['side'] = self.switch_order_side()
            # Send email if monitoring is enabled.
            #self._send_status_email(order)
            # Log the order data.
            self._log_order_status(order)
            return

        else:

            self.state['price'] = self.strategy.loop_signal_price

            # Check which set of order prices we should use.
            if self.state['side'] == 'buy' and market_price < self.state['price'] \
            or self.state['side'] == 'sell' and market_price > self.state['price']:
                return

            # Generate the order parameters.
            order_params = self.order_parameters()

            # Try to create the order.
            order = self.submit_order(order_params)

            self.log.info('Created loop order: {}'.format(order_params))

            if not order:
                self.log.warning('Creating loop order failed.')
                self.cancel_symbol_orders()
                return

            filled, status, order = self.wait_for_fill(order)

            if not filled:
                self.log.warning('Loop order failed with status: {}'.format(status))
                self.cancel_symbol_orders()
                return

            self.log.info('Loop order filled.')
            self.state['last_order'] = order
            self.state['side'] = self.switch_order_side()
            # Send email if monitoring is enabled.
            #self._send_status_email(order)
            # Log the order data.
            self._log_order_status(order)
            return

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
        jump_loop_order = self.strategy.jump_loop_order
        jump_limit_spread = self.strategy.jump_limit_spread
        initial_oco_price = self.strategy.initial_oco_price

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
            self.strategy.jump_buy_limit_price = loop_signal_price + jump_loop_order + jump_limit_spread
            self.strategy.jump_sell_limit_price = loop_signal_price - jump_loop_order - jump_limit_spread
            self.strategy.jump_buy_stop_price = None
            self.strategy.jump_sell_stop_price = None

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
            self.strategy.jump_buy_limit_price = None
            self.strategy.jump_sell_limit_price = None
            self.strategy.jump_buy_stop_price = loop_signal_price + jump_loop_order
            self.strategy.jump_sell_stop_price = loop_signal_price - jump_loop_order

        if self.strategy.initial_order_type == 'stop_limit':
            self.strategy.initial_buy_stop_price = initial_trade_price
            self.strategy.initial_sell_stop_price = initial_trade_price
            self.strategy.initial_buy_limit_price = self.strategy.initial_buy_stop_price + initial_limit_spread
            self.strategy.initial_sell_limit_price = self.strategy.initial_buy_stop_price - initial_limit_spread

        if self.strategy.loop_order_type == 'stop_limit':
            self.strategy.loop_buy_stop_price = loop_signal_price + loop_trade_spread
            self.strategy.loop_sell_stop_price = loop_signal_price - loop_trade_spread
            self.strategy.loop_buy_limit_price = self.strategy.loop_buy_stop_price + loop_limit_spread
            self.strategy.loop_sell_limit_price = self.strategy.loop_sell_stop_price - loop_limit_spread

            self.strategy.jump_buy_stop_price = loop_signal_price + jump_loop_order
            self.strategy.jump_sell_stop_price = loop_signal_price - jump_loop_order
            self.strategy.jump_buy_limit_price = self.strategy.jump_buy_stop_price + jump_limit_spread
            self.strategy.jump_sell_limit_price = self.strategy.jump_sell_stop_price - jump_limit_spread

        # OCO orders are handles as special case.
        # Initial OCO order.
        self.strategy.oco_initial_buy_limit_price = initial_oco_price - initial_limit_spread
        self.strategy.oco_initial_sell_limit_price = initial_oco_price + initial_limit_spread
        self.strategy.oco_initial_buy_stop_price = initial_oco_price
        self.strategy.oco_initial_sell_stop_price = initial_oco_price

        # Loop OCO orders.
        self.strategy.oco_buy_limit_price = self.strategy.oco_limit_price
        self.strategy.oco_sell_limit_price = self.strategy.oco_limit_price
        self.strategy.oco_buy_stop_price = loop_signal_price + loop_trade_spread
        self.strategy.oco_sell_stop_price = loop_signal_price - loop_trade_spread
        # Jump OCO orders.
        self.strategy.oco_jump_buy_limit_price = self.strategy.oco_limit_price + jump_loop_order + jump_limit_spread
        self.strategy.oco_jump_sell_limit_price = self.strategy.oco_limit_price + jump_loop_order + jump_limit_spread
        self.strategy.oco_jump_buy_stop_price = loop_signal_price - jump_loop_order
        self.strategy.oco_jump_sell_stop_price = loop_signal_price - jump_loop_order

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

        # Check if email notifications are enabled.
        if not self.strategy.enable_email_monitoring:
            return

        # The time difference is current time minus last email time in seconds.
        time_diff = time.time() - self.last_email_timestamp

        # We need to convert the email frequency to monutes by multiplying it with
        # 60 because the time difference we are going to compare it with is in seconds
        # while the email_monitoring_frequency is intended to represent minutes.
        email_frequency_in_minutes = self.strategy.email_monitoring_frequency * 60

        # Initially we will assume the subject is normal statis update and
        # it should not be send immediately.
        send_immediately = False
        subject = 'Status update'

        # If the last order was filled we want to send immediate alert.
        if order['status']== 'filled':
            send_immediately = True
        if order['status'] == 'rejected':
            subject = 'Rejected order'
            send_immediately = True

        if (time_diff >= email_frequency_in_minutes) or send_immediately:
            message = '''
            Open Position: {position_size} {position_symbol} <br>
            Active Order: {side} {quantity} {symbol} <br>
            Order Status: {status}
            '''

            # Get the current open position size. If there is no open position for the symbol
            # the get_position function will return None. In this case we set position_size to 0.
            position = self.get_position()
            if position:
                position_size = position['qty']
            else:
                position_size = 0

            # Add variables to the message template.
            message = message.format(
                symbol=order['symbol'],
                side=order['side'],
                quantity=order['qty'],
                status=order['status'],
                position_symbol=self.symbol,
                position_size=position_size)

            # Send the email.
            self.email_sender.send(
                from_email=self.config.email_monitoring_sending_email,
                to_email=self.config.email_monitoring_receiving_email,
                subject=subject,
                message=message)

            # Update the last email timestamp.
            self.last_email_timestamp = time.time()

    def _send_termination_alert(self, reason):
        '''
        Called when the system is terminating.
        '''
        subject = 'Terminating'
        message = '''
        The system has terminated.<br>
        Reason: {reason}
        '''
        message = message.format(reason=reason)

        result = self.email_sender.send(
            from_email=self.config.email_monitoring_sending_email,
            to_email=self.config.email_monitoring_receiving_email,
            subject=subject,
            message=message)
        return result

    def _terminate(self, reason=None):
        '''
        Cancel all orders and terminate the system.

        Arguments:
        reason (str) : The reason for the termination.
        '''
        if reason:
            self.log.info(reason)
        self.log.info(f'Canceling all {self.symbol} orders and terminating.')
        self.cancel_symbol_orders()
        raise SystemExit

    def _submit_order_with_instructions(self, symbol, qty,
                    side, type, time_in_force, limit_price=None,
                    stop_price=None, client_order_id=None,
                    extended_hours=None, order_class=None,
                    take_profit=None, stop_loss=None):
        '''
        This is slightly modified version of the original submit_order
        method of alpaca_trade_api used when we need to add order instructions.
        '''
        params = {
            'symbol':        symbol,
            'qty':           qty,
            'side':          side,
            'type':          type,
            'time_in_force': time_in_force,
            'instructions': self.strategy.order_instructions
        }
        if limit_price is not None:
            params['limit_price'] = float(limit_price)
        if stop_price is not None:
            params['stop_price'] = float(stop_price)
        if client_order_id is not None:
            params['client_order_id'] = client_order_id
        if extended_hours is not None:
            params['extended_hours'] = extended_hours
        if order_class is not None:
            params['order_class'] = order_class
        if take_profit is not None:
            if 'limit_price' in take_profit:
                take_profit['limit_price'] = float(
                    take_profit['limit_price'])
            params['take_profit'] = take_profit
        if stop_loss is not None:
            if 'limit_price' in stop_loss:
                stop_loss['limit_price'] = float(
                    stop_loss['limit_price'])
            if 'stop_price' in stop_loss:
                stop_loss['stop_price'] = float(
                    stop_loss['stop_price'])
            params['stop_loss'] = stop_loss
        resp = self.client.post('/orders', params)
        return alpaca_order(resp)
