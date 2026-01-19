from django.urls import path, include
from rest_framework.routers import DefaultRouter
from app.views import AuctionWatcherViewSet, BidViewSet ,AuctionViewSet, CategoryListView, ExhibitionViewSet, FaQDetail, FaQListCreate, GalleryItemDetail, GalleryItemListCreate, ItemViewSet, SectionDetailView, SendEmailFormView, my_auctions, auction_bids, SectionsApiView, auction_request
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'auctions', AuctionViewSet)
router.register(r'items', ItemViewSet)
router.register(r'auction-watchers', AuctionWatcherViewSet, basename='auction-watcher')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/auctions/<int:pk>/bids/', auction_bids, name='auction-bids'),
    path('api/sections/<int:pk>/', SectionDetailView.as_view(), name='section-detail'),
    path('api/gallery-items/', GalleryItemListCreate.as_view(), name='gallery-item-list-create'),
    path('api/gallery-items/<int:pk>/', GalleryItemDetail.as_view(), name='gallery-item-detail'),
#    path('api/gallery-items/<int:pk>/update/', GalleryItemUpdateView.as_view(), name='gallery-item-update'),
#    path('api/gallery-items/<int:pk>/delete/', GalleryItemDeleteView.as_view(), name='gallery-item-delete'),
    path('api/my_auctions/', my_auctions, name='my-auctions'),
    path('api/exhibitions/', ExhibitionViewSet.as_view({'get': 'list', 'post': 'create'}), name='exhibition-list'),
    path('api/exhibitions/<int:pk>/', ExhibitionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='exhibition-detail'),
    path('api/send_email/', SendEmailFormView.as_view(), name="send_email"),
    path('api/categories/', CategoryListView.as_view(), name="category-list-view"),
    path('accounts/', include('accounts.urls')),  # Include the accounts URLs
    path('get_sections/', SectionsApiView.as_view(), name="get-sections"),
    path('api/bids/by-auction/', BidViewSet.as_view({'get': 'bids_by_auction'}), name='bids_by-auction'),  # Bids by auction URL
    path('api/send_auction_request/', auction_request, name="send-auction-request"),
    path('api/faq/', FaQListCreate.as_view(), name="faq-list-create"),
    path('api/faq/<int:pk>/', FaQDetail.as_view(), name="faq-detail"),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
