'''
General configuration variables for Trader.
'''

# API credentials.
api_key = ''
api_secret = ''

# Set to True in order to use paper-trading.
use_sandbox = True

# The level of the logs. Valid values: DEBUG, INFO, WARNING, ERROR
log_level = 'INFO'

# The systems logs will be saved to this file.
log_file = 'my_log_file.txt'

# Enable/disable logging to the console.
console_log = True

# If there are any errors the system will wait for sleep_after_errors
# seconds before retrying.
sleep_after_error = 1

# The update time is the number of seconds to wait before attempting data pull.
# Note that the API rate limit is 200 calls per minute, which means that we can make
# approximately 3 calls per second. Therefore the minimal safe value for update_time is 0.3
update_time = 1
