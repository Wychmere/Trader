# Trader
Alpaca trading strategy

### Requirements
To run it you will need Python version 3.7 or above and the ```alpaca-trade-api``` library installed.
To install all requirements you can use this command:
```pip install -r requirements.txt```

### How to run the system
Before starting the system you have to edit ```config.py``` where you have to add your API credentials and ```strategy.py``` where you can adjust various parameters related to the system.
After this you can start the trader by tying:
```python main.py```

### Notes
In ```config.py``` you will find the ```use_sandbox``` variable. If it is set to True and you have added the correct API credentials the trader will start trading with you live account.