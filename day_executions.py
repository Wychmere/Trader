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
import os
import csv
import pytz
import config
import socket
import pathlib
import argparse
import datetime
import http.server
import socketserver
import alpaca_trade_api as tradeapi


def serve(filename):
    os.system('mkdir tmp')
    os.system('cp {0} tmp/{0}'.format(filename))
    os.chdir('tmp/')

    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    handler = http.server.SimpleHTTPRequestHandler

    with socketserver.TCPServer(('', 8000), handler) as httpd:
            print(f'Download URL: http://{ip_address}:8000')
            httpd.serve_forever()


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
    Pull the account FILL activities for given date and saves it to CSV file.
    Example:
    python day_executions -output my_file.csv -date 2020-07-24
    python day_executions -output my_file.csv -date_range "2020-07-20 - 2020-07-30"
    '''
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-output', type=str, default=None,
                        help='the output filename')
    parser.add_argument('-date', type=str, default=None,
                        help='the date to pull data for in YYYY-MM-DD format')
    parser.add_argument('-date_range', type=str, default=None,
                        help='the date range to pull data for in YYYY-MM-DD format')
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

    # Select a date.
    tz = pytz.timezone('America/New_York')
    if args.date:
        start_date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
        end_date = start_date + datetime.timedelta(days=1)
        start_date = start_date.replace(tzinfo=tz)
        end_date = end_date.replace(tzinfo=tz)
        dates = [[start_date, end_date]]

    elif args.date_range:
        date_range_start, date_range_end = args.date_range.split(' - ')
        start_date = datetime.datetime.strptime(date_range_start, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(date_range_end, '%Y-%m-%d')
        start_date = start_date.replace(tzinfo=tz)
        end_date = end_date.replace(tzinfo=tz)

        one_day = datetime.timedelta(days=1)
        dates = [[start_date, start_date + one_day]]
        for _ in range((end_date - start_date).days):
            next_date = dates[-1][1] + one_day
            dates.append([dates[-1][1], next_date])
    else:
        #start_date = datetime.datetime(2020, 7, 28, tzinfo=tz)
        start_date = datetime.datetime.utcnow().date()
        end_date = (start_date + datetime.timedelta(days=1))
        dates = [[start_date, end_date]]

    orders = []
    for start_date, end_date in dates:
        days_orders = client.list_orders(
            limit=500,
            after=start_date.isoformat(),
            until=end_date.isoformat(),
            status='all')
        orders.extend([o._raw for o in days_orders])

    print(orders)

    # Save to file.
    if args.output:
        to_csv(orders, args.output)
        serve(args.output)


if __name__ == '__main__':
    main()
