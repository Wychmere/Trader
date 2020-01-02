from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class EmailSender:
    '''
    Simple sendgrid email sending module.

    Arguments:
    api_key (str) : The sendgrid api key.
    '''

    def __init__(self, api_key):
        self.client = SendGridAPIClient(api_key)

    def send(self, from_email, to_email, subject, message):
        '''
        Send email.

        Arguments:
        from_email (str) : The sending email address.
        to_email (str) : The receiving email address.
        subject (str) : The subject line.
        message (str) : The body of the email.
        '''
        email_data = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content='<p>{}</p>'.format(message))
        response = self.client.send(email_data)
        return response
