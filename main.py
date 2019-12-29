'''
This script imports the configuration and strategy modules
and runs the trading system.
'''

import trader
import config
import strategy

if __name__ == '__main__':
    # Create the trader.
    tr = trader.Trader(
        api_key=config.api_key,
        api_secret=config.api_secret,
        config=config,
        strategy=strategy)

    # Run forever.
    tr.run_forever()
