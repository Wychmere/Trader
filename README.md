# Trader
Alpaca trading strategy

### Requirements
To run it you will need:
Python version 3.7 or above.
The ```alpaca-trade-api``` library.
The ```sendgrid``` library.
To install all requirements you can use this command:
```pip install -r requirements.txt```

### How to run the system
Before starting the system you have to edit ```config.py``` where you have to add your API credentials and ```strategy.py``` where you can adjust various parameters related to the system.

Then you need to start the zmq_msg server using the run_forever script by typing:
```python run_forever.py python zmq_msg.py```

You also need to start the the Streamer interface that will collect data about orders execution:
```python run_forever.py python streamer.py```

After this you can start the trader by tying:
```python main.py```

### Notes
In ```config.py``` you will find the ```use_sandbox``` variable. If it is set to True and you have added the correct API credentials the trader will start trading with you live account.

As all three elements of the system - Trader, Streamer and zmq_msg are going to block the terminal you
will have to use tmux to start each one in a separate terminal.
To create new terminals in tmux you can pres ctrl+b + c
To navigate between terminals you can use ctrl+b followed by the number of the terminal (starting from 0)