'''
This script pulls the account FILL activities for given date
and saves it to CSV file.

Args:
-output (str)
    The filename of the CSV file to be generated. If not
    specified the output will only be printed on screen.
-date (str)
    The data for which to pull data in YYYY-MM-DD format.
    If not specified the data for the current day will
    be pulled.

Example:
python3 day_executions -output my_file.csv -date 2020-07-24
'''

import sys
import csv
import pytz
import config
import pathlib
import argparse
import datetime
import dateutil.parser
import alpaca_trade_api as tradeapi


def to_csv(rows, filename):
    f = pathlib.Path(filename)
    add_header = not f.exists()
    writer = csv.DictWriter(
        f.open('a', newline=''),
        fieldnames=rows[0].keys())
    if add_header:
        writer.writeheader()
    writer.writerows(rows)


def arguments():
    description = '''
    Pull the account FILL activities for given date
    and saves it to CSV file.
    Args:
    -output
    The filename of the CSV file to be generated. If not
    specified the output will only be printed on screen.
    -date
    The data for which to pull data in YYYY-MM-DD format.
    Defaults to current date.
    Example:
    python3 day_executions -output my_file.csv -date 2020-07-24
    '''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-output', type=str, default=None)
    parser.add_argument('-date', type=str, default=None)
    return parser.parse_args()

def main():
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

    # Get arguments.
    args = arguments()

    # Select a data.
    if args.date:
        date = args.date
    else:
        tz = pytz.timezone('America/New_York')
        date = datetime.datetime.now(tz).strftime('%Y-%m-%d')

    # Get account data.
    raw_fills = client.get_activities(activity_types='FILL', date=date)

    def process_fill(f):
        to_keep = ['transaction_time', 'price', 'qty', 'side',
                   'symbol', 'leaves_qty', 'order_id', 'cum_qty']
        processed = {k: v for k, v in f._raw.items() if k in to_keep}
        date = dateutil.parser.isoparse(processed['transaction_time'])
        processed['transaction_time'] = date.strftime('%Y-%m-%d %H:%M:%S')
        return processed

    fills = [process_fill(f) for f in raw_fills]

    if not fills:
        print(f'No data for {date}')
        return

    print(fills)

    # Save to file.
    if args.output:
        to_csv(fills, args.output)

if __name__ == '__main__':
    main()
