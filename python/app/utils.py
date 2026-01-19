import re
import uuid
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from twilio.rest import Client
from django.conf import settings
import uuid
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .tasks import send_notification_task

def compress_image(image, randomizeName=False):
    with Image.open(image) as img:
        output_format = img.format
        
        output_io = BytesIO()
        
        img.save(output_io, format=output_format, quality=70)
        output_io.seek(0)
        
        if randomizeName:
            filename = f"{uuid.uuid4().hex}.{output_format.lower()}"
        else:
            filename = image.name
        
        compressed_image = InMemoryUploadedFile(
            output_io,
            'ImageField',
            filename,
            image.content_type,
            output_io.tell(),
            None
        )
    
    return compressed_image

def schedule_auction_notification(auction_id, delay_minutes=2):
    """
    Schedule a notification task for the auction.
    
    :param auction_id: The ID of the auction to notify about.
    :param delay_minutes: Number of minutes to delay the notification task.
    """
    send_notification_task(auction_id, schedule=timedelta(minutes=delay_minutes))


def strip_html_tags(text):
    text = re.sub(r'<p\s*[^>]*>', '\n\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<.*?>', '', text)
    return text



def send_sms(to, body):
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    twilio_phone_number = settings.TWILIO_PHONE_NUMBER

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=body,
        from_=twilio_phone_number,
        to=to
    )

    return message.sid