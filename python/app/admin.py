from django.contrib import admin
from .models import Auction, Bid, Section

class AuctionAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'year', 'medium', 'current_bid', 'end_date')
    search_fields = ('title', 'artist', 'year')
    list_filter = ('year', 'medium', 'end_date')

class BidAdmin(admin.ModelAdmin):
    list_display = ('auction', 'user', 'amount', 'date')
    search_fields = ('auction__title', 'user__username')
    list_filter = ('auction', 'date')
    
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'title2')
    search_fields = ('title', 'title2')
    list_filter = ('title', 'title2')

admin.site.register(Auction, AuctionAdmin)
admin.site.register(Bid, BidAdmin)
admin.site.register(Section, SectionAdmin)