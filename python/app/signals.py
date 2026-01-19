from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Bid
from .tasks import send_notification_task

#@receiver(post_save, sender=Bid)
#def schedule_notification(sender, instance, created, **kwargs):
#    if created:
#        print(f"Scheduling notification for auction id {instance.auction.id}")
#        send_notification_task.schedule(timedelta(minutes=2), auction_id=instance.auction.id)