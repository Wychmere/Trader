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
buy_limit_price = 199
buy_stop_price = None

sell_limit_price = 220
sell_stop_price = None

buy_stop_price = 199
sell_stop_price = 201

# Valid values for time_in_force: day, gtc, opg, cls, ioc, fok
time_in_force = 'gtc'
