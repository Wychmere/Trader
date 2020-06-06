'''
Variables related to the strategy executed by Trader.
'''

symbol = 'AAPL'
quantity = 1
initial_order_side = 'sell'
initial_order_type = 'limit'
loop_order_type = 'limit'

# Use OCO for the initial order.
oco_initial_order = True
initial_oco_price = 239

# TODO add documentation about the usage of price and spread variables.
# The initial order prices will be used only for the first order.
initial_trade_price = 239
initial_limit_spread = 1

# The loop order prices will be used for each order after the initial one.
loop_signal_price = 220
loop_trade_spread = 2
loop_limit_spread = 2

# The jump spreads will be used if the order is rejected with the loop spread.
jump_loop_order = 4
jump_limit_spread = 4

# Use OCO orders for the loop.
oco_loop_order = True
oco_limit_price = 270

# Valid values for time_in_force: day, gtc, opg, cls, ioc, fok
time_in_force = 'gtc'

# Enable/disable email monitoring.
enable_email_monitoring = True

# The frequency (in minutes) at which to send monitoring emails.
email_monitoring_frequency = 1
