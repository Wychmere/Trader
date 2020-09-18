import zmq
import time
import logging
import traceback

class Server:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind("tcp://*:5555")

        self.last_updated = time.time()
        self.orders = {}
        self.prices = {}

    def run(self):
        while True:
            message = self.socket.recv_json()
            if message['action'] == 'read':
                response = {
                    'last_updated': self.last_updated,
                    'orders': self.orders,
                    'prices': self.prices}
                self.socket.send_json(response, zmq.NOBLOCK)

            elif message['action'] == 'write':
                self.last_updated = time.time()
                if message['type'] == 'order':
                    order = message['data']
                    self.orders[order['id']] = order
                elif message['type'] == 'price':
                    symbol = message['data']['symbol']
                    price = message['data']['price']
                    timestamp = message['data']['timestamp']
                    self.prices[symbol] = {'price': price, 'timestamp':timestamp}
                self.socket.send_json({'status': 'ok'})


class Client:
    def __init__(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:5555")

    def read(self):
        message = {'action': 'read'}
        self.socket.send_json(message)
        return self.socket.recv_json()

    def write(self, type, data):
        message = {
            'action': 'write',
            'type': type,
            'data': data}
        self.socket.send_json(message)
        self.socket.recv_json()


def construct_logger(filename):
    log_headers = [logging.FileHandler(filename), logging.StreamHandler()]
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=log_headers)
    return logging.getLogger(__name__)

if __name__ == '__main__':
    log = construct_logger('zmq_server.log')
    try:
        zmq_server = Server()
        zmq_server.run()
    except:
        zmq_server.context.destroy()
        err = traceback.format_exc()
        log.error(f'ZMQ failed: {err}')
        time.sleep(5)
