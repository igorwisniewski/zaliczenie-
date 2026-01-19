# utils.py
from twilio.rest import Client
from django.conf import settings
import uuid
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta

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

def send_verification_code_email(instance):
    if not instance.email_verification_token:
        instance.email_verification_token = str(uuid.uuid4())
    instance.email_verification_expiry = timezone.now() + timedelta(days=1)
    instance.save()

    template_name = "email_templates/verify_email_django.html"
    verification_url = f"https://cncgart.pl/verify-email/{instance.email_verification_token}/"

    context = {
        "verification_url": verification_url,
        "username": instance.username,
        "email": instance.email,
    }

    html_content = render_to_string(template_name, context)
    try:
        send_mail(
        subject='Verify your email',
        message=f'Click the link to verify your email: {verification_url}',
        recipient_list=[instance.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
        fail_silently=False,
        html_message=html_content,
        )
    except Exception as e:
        print(str(e))