from django.core.management.base import BaseCommand
from app.models import Auction

class Command(BaseCommand):
    help = 'Update every auction that has no buy_now_price'

    def handle(self, *args, **kwargs):
        auctions = Auction.objects.filter(buy_now_price__isnull=True)
        updated_count = 0

        for auction in auctions:
            auction.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} auctions'))
