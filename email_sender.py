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

    def send(self, from_email, to_email, subject, message, retry=3):
        '''
        Send email.

        Arguments:
        from_email (str) : The sending email address.
        to_email (str) : The receiving email address.
        subject (str) : The subject line.
        message (str) : The body of the email.

        Returns:
        On success: 'Email sent.'
        On error: The exception message.
        '''
        error = None
        result = None
        while retry >= 0:
            try:
                email_data = Mail(
                    from_email=from_email,
                    to_emails=to_email,
                    subject=subject,
                    html_content='<p>{}</p>'.format(message))
                self.client.send(email_data)
                result = 'Email sent.'
                break
            except Exception as ex:
                retry -= 1
                error = ex
        return result if result else error
