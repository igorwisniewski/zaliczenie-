from background_task import background
from django.utils import timezone
from datetime import timedelta

from .utils import send_verification_code_email

@background(schedule=15)
def send_verification_code_email_task(user_id):
    from .models import MyUser
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    import uuid

    user = MyUser.objects.get(id=user_id)
    if user is None:
        return

    #print(f"Running task for {user.username}")
    send_verification_code_email(instance=user)
    #print("Task done")
