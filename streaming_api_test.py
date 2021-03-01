'''
This script connects to the streaming API V2.
Ref: https://alpaca.markets/docs/api-documentation/api-v2/market-data/alpaca-data-api-v2/real-time/
'''
import json
import datetime
from websocket import create_connection

API_KEY = ''
API_SECRET = ''

LOG_FILE = open('streaming_api_test.log', 'w')


def log(msg):
    now = datetime.datetime.now()
    msg = f'{now} {msg}'
    print(msg)
    LOG_FILE.write(msg + '\n')


def main():
    url = 'wss://stream.data.alpaca.markets/v2/sip'
    ws = create_connection(url)
    msg = ws.recv()
    log(msg)

    ws.send(
        json.dumps({"action": "auth", "key": API_KEY, "secret": API_SECRET})
    )
    msg = ws.recv()
    log(msg)

    ws.send(
        json.dumps( {"action": "subscribe", "trades": ["AAPL"]})
    )
    msg = ws.recv()
    log(msg)

    for _ in range(20):
        msg = json.loads(ws.recv())
        log(msg)


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        log(err)
        LOG_FILE.close()
