from datetime import timedelta
from background_task import background
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from .models import Auction, AuctionWatcher, Bid, NotificationLog

NOTIFICATION_INTERVAL = timedelta(minutes=5)  # Set the interval to 5 minutes

@background(schedule=120)
def send_notification_task(auction_id):
    try:
        auction = Auction.objects.get(id=auction_id)
        latest_bid = auction.bids.latest('date')

        latest_bidder = latest_bid.user
        watchers = AuctionWatcher.objects.filter(auction=auction)

        for watcher in watchers:
            if watcher.notify_via_email and watcher.user != latest_bidder:
                last_notification = NotificationLog.objects.filter(
                    user_email=watcher.user.email,
                    auction_id=auction_id
                ).first()

                if not last_notification or timezone.now() - last_notification.last_notified_at > NOTIFICATION_INTERVAL:
                    print(f"Running notifications for {watcher.user.email}")
                    send_email_notification(watcher.user.email, auction)
                    NotificationLog.objects.update_or_create(
                        user_email=watcher.user.email,
                        auction_id=auction_id,
                        defaults={'last_notified_at': timezone.now()}
                    )
                else:
                    print(f"Skipping notification for {watcher.user.email}, last notified too recently.")

    except Auction.DoesNotExist:
        print(f"Auction with id {auction_id} does not exist.")
    except Bid.DoesNotExist:
        print(f"No bids found for auction with id {auction_id}.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def send_email_notification(email, auction):
    from .utils import strip_html_tags
    subject = f'New Bid on Auction: {auction.title}'
    html_message = render_to_string('auction/new_bid.html', {'auction': auction})
    message = strip_html_tags(html_message)
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email],
        html_message=html_message
    )
