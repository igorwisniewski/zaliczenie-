from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuctionListCreate, AuctionUpdate, AuctionViewSet, AuctionWatcherViewSet, BidUpdateView, BidViewSet, CategoryListView, GalleryItemDetail, GalleryItemListCreate, ItemListCreate, ItemUpdate, ItemViewSet, SectionDetailView, SectionViewSet, auction_request, my_auctions, auction_bids, user_bids, ExhibitionViewSet, FaQDetail, FaQListCreate

router = DefaultRouter()
router.register(r'auctions', AuctionViewSet)
router.register(r'items', ItemViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'exhibitions', ExhibitionViewSet, basename='exhibition')
router.register(r'bids', BidViewSet, basename='bid')
router.register(r'auction-watchers', AuctionWatcherViewSet, basename='auction-watcher')


urlpatterns = [
    path('', include(router.urls)),
    path('my-auctions/', my_auctions, name='my-auctions'),
    path('auctions/<int:pk>/bids/', auction_bids, name='auction-bids'),
    path('api/auctions/<int:pk>/update/', AuctionUpdate.as_view(), name='auction-update'),
    path('api/items/<int:pk>/update/', ItemUpdate.as_view(), name='item-update'),
    path('api/sections/<int:pk>/', SectionDetailView.as_view(), name='section-detail'),
    path('api/gallery-items/', GalleryItemListCreate.as_view(), name='gallery-item-list-create'),
    path('api/gallery-items/<int:pk>/', GalleryItemDetail.as_view(), name='gallery-item-detail'),
    path('bids/<int:pk>/update/', BidUpdateView.as_view(), name='bid-update'),
    path('user-bids/', user_bids, name='user-bids'),
    path('api/categories/', CategoryListView.as_view(), name="category-list-view"),
    path('api/exhibitions/', ExhibitionViewSet.as_view({'get': 'list', 'post': 'create'}), name='exhibition-list'),
    path('api/exhibitions/<int:pk>/', ExhibitionViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='exhibition-detail'),
    path('api/bids/by-auction/', BidViewSet.as_view({'get': 'bids_by_auction'}), name='bids_by-auction'),
    path('api/auctions/', AuctionListCreate.as_view(), name='auction-list-create'),
    path('api/items/', ItemListCreate.as_view(), name='item-list-create'),
    path('api/send_auction_request/', auction_request, name="send-auction-request"),
    path('api/faq/', FaQListCreate.as_view(), name="faq-list-create"),
    path('api/faq/<int:pk>/', FaQDetail.as_view(), name="faq-detail"),
]
