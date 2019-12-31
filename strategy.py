'''
Variables related to the strategy executed by Trader.
'''

symbol = 'AAPL'
quantity = 1
first_order_side = 'buy'
initial_order_type = 'stop'
loop_order_type = 'stop'

# TODO add documentation about the usage of price and spread variables.
# The initial order prices will be used only for the first order.
initial_trade_price = 290
initial_limit_spread = 2

# The loop order prices will be used for each order after the initial one.
loop_signal_price = 220
loop_trade_spread = 2
loop_limit_spread = 2

# Valid values for time_in_force: day, gtc, opg, cls, ioc, fok
time_in_force = 'gtc'
