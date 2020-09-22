echo Starting zmq_msg and streamer.
nohup python3 run_forever.py python3 zmq_msg.py &
nohup python3 run_forever.py python3 streamer.py &