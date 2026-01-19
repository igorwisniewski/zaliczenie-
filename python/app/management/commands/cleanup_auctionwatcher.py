from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import Auction, AuctionWatcher

class Command(BaseCommand):
    help = 'Removes AuctionWatchers for ended auctions'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # Get the IDs of auctions that have ended
        ended_auction_ids = Auction.objects.filter(end_date__lte=now).values_list('id', flat=True)
        
        if not ended_auction_ids:
            self.stdout.write(self.style.SUCCESS('No ended auctions found.'))
            return
        
        # Delete related notification logs
        auctionwatchers_deleted, _ = AuctionWatcher.objects.filter(auction_id__in=ended_auction_ids).delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully removed {auctionwatchers_deleted} auction watchers for ended auctions.'))
