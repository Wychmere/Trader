'''
General configuration variables for Trader.
'''

# API credentials.
api_key = 'PKPIHL3MCWPPH4NXOA78'
api_secret = 'rArHDGVszKecHehqcliWTcmxLpGhuXkgoXOKcv1u'

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

# The update time is the number of seconds to wait before updates. As we
# are using streaming data this parameter can be set to very low values
# like 0.0001.
update_time = 0.0001

# After sending an order to the exchange Trader will check its status after that amount of seconds.
order_status_check_delay = 3

# The Sendgrid API key used for email monitoring.
sendgrid_api_key = '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'

# The sending email address used for email monitoring.
email_monitoring_sending_email = 'trader@trader.io'

# The receiving email address used for email monitoring.
email_monitoring_receiving_email = ''
