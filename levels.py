'''
This script pulls the account information and prints it on the screen.
The account credentials are taken from the config.py file used by Trader.
If a filename is given as command line argument the same result will
be saved in that file. If the file exists it will be appended to.

Example:
python3 levels.py my-levels.txt
'''

import sys
import config
import datetime
import alpaca_trade_api as tradeapi

if __name__ == '__main__':
    # Set the base url.
    if config.use_sandbox:
        base_url = 'https://paper-api.alpaca.markets'
    else:
        base_url = 'https://api.alpaca.markets'

    # Create the Alpaca API client.
    client = tradeapi.REST(
        key_id=config.api_key,
        secret_key=config.api_secret,
        base_url=base_url,
        api_version='v2')

    # Get account data.
    account = client.get_account()._raw

    # The list of items to drop from the received data.
    drop_items = ('account_number', 'status', 'trading_blocked',
                  'transfers_blocked', 'account_blocked', 'id',
                  'created_at', 'trade_suspended_by_user')
    data = [f'{k}: {v}' for k, v in account.items() if k not in drop_items]

    # Prepare the string output.
    string_data = '\n'.join(data)
    timestamp = '\nDate: {}\n'.format(datetime.datetime.now())
    line = '\n{}'.format('#'*50)
    result = line + timestamp + string_data

    print(result)

    # Save to file.
    if len(sys.argv) == 2:
        with open(sys.argv[1], 'a') as f:
            f.write(result)
