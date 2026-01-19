from django.db.models.signals import post_save
from django.dispatch import receiver

from .utils import send_verification_code_email
from .tasks import send_verification_code_email_task
from .models import MyUser

@receiver(post_save, sender=MyUser)
def send_verification_email(sender, instance, created, **kwargs):
    if created and not instance.is_verified:
        #send_verification_code_email(instance=instance)
        send_verification_code_email_task(user_id=instance.id)

@receiver(post_save, sender=MyUser)
def send_verification_sms(sender, instance, created, **kwargs):
    if created and instance.phone_number and not instance.is_phone_verified:
        instance.send_phone_verification_code()
