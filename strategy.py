'''
Variables related to the strategy executed by Trader.
'''

symbol = 'AAPL'
quantity = 1
first_order_side = 'buy'
first_order_type = 'limit'

# For Market orders set all prices to None.
# For Limit orders set stop prices to None.
# For Stop Limit orders set both limit and stop prices to some value.
# For Stop orders set stop prices to some value.

# The initial order prices will be used only for the first order.
initial_buy_limit_price = 199
initial_buy_stop_price = None

initial_sell_limit_price = 220
initial_sell_stop_price = None

initial_buy_stop_price = 199
initial_sell_stop_price = 201

# The loop order prices will be used for each order after the initial one.
loop_buy_limit_price = 200
loop_buy_stop_price = None

loop_sell_limit_price = 225
loop_sell_stop_price = None

loop_buy_stop_price = 200
loop_sell_stop_price = 210

# Valid values for time_in_force: day, gtc, opg, cls, ioc, fok
time_in_force = 'gtc'
