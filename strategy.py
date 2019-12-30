'''
Variables related to the strategy executed by Trader.
'''

symbol = 'AAPL'
quantity = 1
first_order_side = 'buy'
initial_order_type = 'stop'
loop_order_type = 'limit'

# For Market orders set all prices to None.
# For Limit orders set stop prices to None.
# For Stop Limit orders set both limit and stop prices to some value.
# For Stop orders set stop prices to some value.

# The initial order prices will be used only for the first order.
initial_buy_limit_price = 295
initial_buy_stop_price = 296

initial_sell_limit_price = 222
initial_sell_stop_price = 221

# The loop order prices will be used for each order after the initial one.
loop_buy_limit_price = 219
loop_buy_stop_price = 218

loop_sell_limit_price = 222
loop_sell_stop_price = 221

# Valid values for time_in_force: day, gtc, opg, cls, ioc, fok
time_in_force = 'gtc'
