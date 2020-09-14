'''
Variables related to the strategy executed by Trader.
'''

symbol = 'MSFT'
quantity = 1
initial_order_side = 'sell'
initial_order_type = 'limit'
order_instructions = 'alpaca::wexc-algo=destination=STOCK-DMA'

# TODO add documentation about the usage of price and spread variables.
# The initial order prices will be used only for the first order.
initial_signal_price = 239
initial_limit_spread = 1

# The loop order prices will be used for each order after the initial one.
loop_signal_price = 220

# Valid values for time_in_force: day, gtc, opg, cls, ioc, fok
time_in_force = 'gtc'

# Enable/disable email monitoring.
enable_email_monitoring = True

# The frequency (in minutes) at which to send monitoring emails.
email_monitoring_frequency = 1
