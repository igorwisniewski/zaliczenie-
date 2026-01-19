from datetime import timedelta
from django.conf import settings
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework import status, generics, viewsets, mixins

from .utils import compress_image, schedule_auction_notification, strip_html_tags
from .models import Auction, AuctionWatcher, Bid, Category, Exhibition, FaQ, GalleryItem, Item, Section
from .serializers import AuctionRequestSerializer, AuctionSerializer, AuctionSerializerUpdate, AuctionWatcherSerializer, BidSerializer, CategorySerializer, ExhibitionSerializer, FaQSerializer, GalleryItemSerializer, ItemSerializer, ItemSerializerUpdate, SectionSerializer, SendEmailSerializer
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission, SAFE_METHODS
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail, EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string

class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_staff


class isStaffUser(BasePermission):
    def has_permission(self, request, view):
         user = request.user
         return user.is_staff

class AuctionListCreate(generics.ListCreateAPIView):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
    permission_classes = [IsAuthenticated&isStaffUser]
    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        return super().create(request, *args, **kwargs)
    
class AuctionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'message': 'Success!'}, status=status.HTTP_200_OK)


    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        self.perform_destroy(self.get_object())
        return Response({'message': 'Success!'}, status=status.HTTP_204_NO_CONTENT)

class AuctionViewSet(viewsets.ModelViewSet):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer


    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated&isStaffUser])
    def delete_selected(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        Auction.objects.filter(id__in=ids).delete()
        return Response({"success": "Selected auctions have been deleted"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_bids(self, request):
        bids = Bid.objects.filter(user=request.user)
        serializer = BidSerializer(bids, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def place_bid(self, request, pk=None):
        auction = self.get_object()
        bid_amount = request.data.get('bid')

        if bid_amount is None:
            return Response({"error": "Oferta nie może być pusta"}, status=status.HTTP_400_BAD_REQUEST)

        bid_amount = float(bid_amount)

        if bid_amount <= auction.current_bid:
            return Response({"error": "Oferta musi być większa niż biezaca cena"}, status=status.HTTP_400_BAD_REQUEST)
        

        # Check if the auction has ended
        if timezone.now() > auction.end_date:
            return Response({"error": "Aukcja się zakończyła, nie można już składać ofert"}, status=status.HTTP_400_BAD_REQUEST)


        # Find the existing bid by the user for this auction
        existing_bid = Bid.objects.filter(auction=auction, user=request.user).first()
        if existing_bid:
            # Update the existing bid
            existing_bid.amount = bid_amount
            existing_bid.date = timezone.now()
            existing_bid.save()
        else:
            # Create a new bid
            Bid.objects.create(auction=auction, user=request.user, amount=bid_amount)

        if timezone.now() >= auction.end_date - timedelta(minutes=5):
                auction.end_date += timedelta(minutes=2)

        auction.current_bid = bid_amount
        auction.save()
        schedule_auction_notification(auction.id)
        return Response({"success": "Oferta została złożona pomyślnie ", "current_bid": auction.current_bid}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def buy_now(self, request, pk=None):
        auction = self.get_object()
        
        # Check if the auction has ended
        if timezone.now() > auction.end_date:
            return Response({"error": "Aukcja się zakończyła, nie można już kupić teraz"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the auction has a buy now price set
        if not auction.buy_now_price:
            return Response({"error": "Cena kup teraz nie jest ustawiona dla tej aukcji"}, status=status.HTTP_400_BAD_REQUEST)
        
        buy_now_price = auction.buy_now_price

        # Find the existing bid by the user for this auction
        existing_bid = Bid.objects.filter(auction=auction, user=request.user).first()
        if existing_bid:
            # Update the existing bid
            existing_bid.amount = buy_now_price
            existing_bid.date = timezone.now()
            existing_bid.save()
        else:
            # Create a new bid
            Bid.objects.create(auction=auction, user=request.user, amount=buy_now_price)
        
        # Update the auction's current bid and end date
        auction.current_bid = buy_now_price
        auction.end_date = timezone.now()
        auction.save()
        
        #schedule_auction_notification(auction.id)
        return Response({"success": "Kup teraz zakończone pomyślnie", "current_bid": auction.current_bid}, status=status.HTTP_201_CREATED)

    

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer


    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated&isStaffUser])
    def delete_selected(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        Item.objects.filter(id__in=ids).delete()
        return Response({"success": "Selected items have been deleted"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def buy_now(self, request, pk=None):
        item = self.get_object()
        if item.buyer is not None:
            return Response({"error": "You can't buy that item!"},  status=status.HTTP_403_FORBIDDEN)
        item.buyer = request.user
        item.save()
        return Response({"success": "Kup teraz zakończone pomyślnie"}, status=status.HTTP_201_CREATED)


class CategoryListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated&isStaffUser]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    pagination_class = None

class BidUpdateView(generics.UpdateAPIView):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bid.objects.filter(user=self.request.user)

@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def user_bids(request):
    user = request.user
    bids = Bid.objects
    serializer = BidSerializer(bids, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_auctions(request):
    user = request.user
    bids = Bid.objects.filter(user=user).select_related('auction')
    auctions_data = []
    for bid in bids:
        auction = bid.auction
        is_winner = auction.current_bid == bid.amount and auction.end_date < timezone.now()
        auctions_data.append({
            'title': auction.title,
            'current_bid': auction.current_bid,
            'status': 'wygrane' if is_winner else 'trwające' if auction.end_date > timezone.now() else 'zakończone',
            'is_winner': is_winner,
            'image': auction.image.url if auction.image else None
        })
    return Response(auctions_data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auction_bids(request, pk):
    try:
        auction = Auction.objects.get(pk=pk)
        bids = auction.bids.order_by('-amount')
        bid_history = [
            {
                'bidder': bid.user.username,
                'amount': bid.amount,
                'date': bid.date,
            }
            for bid in bids
        ]
        return Response(bid_history)
    except Auction.DoesNotExist:
        return Response({"error": "Auction not found"}, status=404)





class AuctionListCreate(generics.ListCreateAPIView):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer
    permission_classes = [IsAuthenticated&isStaffUser]

class AuctionDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'message': 'Success!'}, status=status.HTTP_200_OK)


    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        self.perform_destroy(self.get_object())
        return Response({'message': 'Success!'}, status=status.HTTP_204_NO_CONTENT)

class ItemListCreate(generics.ListCreateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated&isStaffUser]

class ItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'message': 'Success!'}, status=status.HTTP_200_OK)


    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        self.perform_destroy(self.get_object())
        return Response({'message': 'Success!'}, status=status.HTTP_204_NO_CONTENT)

class SectionsApiView(APIView):
    def get(self, request):
        sections = Section.objects.all()
        serializer = SectionSerializer(sections, many=True)
        return Response(serializer.data)
    

@permission_classes([IsAuthenticated])
class AuctionUpdate(generics.RetrieveUpdateAPIView):
    queryset = Auction.objects.all()
    serializer_class = AuctionSerializerUpdate
    permission_classes = [IsAuthenticated&isStaffUser]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    

@permission_classes([IsAuthenticated])
class ItemUpdate(generics.RetrieveUpdateAPIView):
    queryset = Item.objects.all()
    serializer_class = ItemSerializerUpdate
    permission_classes = [IsAuthenticated&isStaffUser]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

class SendEmailFormView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendEmailSerializer(data=request.data)
        if not serializer.is_valid():
           return Response({"error": "form aint valid, dawg"})
        send_mail('Test', f'Imie: {serializer.validated_data["firstName"]}\nNazwisko: {serializer.validated_data["lastName"]}\nEmail: {serializer.validated_data["email"]}\nWyslal wiadomosc: \n{serializer.validated_data["text"]}', 'noreply@cncgart.pl', ['noreply@cncgart.pl'], fail_silently=False,)
        return Response({"message": "Email zostal wyslany!"})
    

class SectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    pagination_class = None
    permission_classes = [isStaffUser]

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    pagination_class = None

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'message': 'Success!'}, status=status.HTTP_200_OK)


    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        self.perform_destroy(self.get_object())
        return Response({'message': 'Success!'}, status=status.HTTP_200_OK)


class GalleryItemListGet(APIView):
    def get(self, request):
        gallery = GalleryItem.objects.all()
        serializer = GalleryItemSerializer(gallery, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GalleryItemListCreate(generics.ListCreateAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer=serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GalleryItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [AllowAny]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None or not request.user.is_staff:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer=serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class GalleryItemUpdateView(generics.UpdateAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAuthenticated, isStaffUser]

class GalleryItemDeleteView(generics.DestroyAPIView):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    permission_classes = [IsAuthenticated, isStaffUser]

class BidViewSet(viewsets.ViewSet):
    queryset = Bid.objects.all()
    serializer_class = BidSerializer
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def bids_by_auction(self, request):
        auctions = Bid.objects.values('auction').distinct()
        results = []
        for auction in auctions:
            bids = Bid.objects.filter(auction=auction['auction']).order_by('-amount')
            if bids:
                highest_bid = bids.first()
                results.append({
                    'auction': highest_bid.auction.title,
                    'highest_bid_user': highest_bid.user.email,
                    'bids': BidSerializer(bids, many=True).data
                })
        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def delete_selected(self, request):
        user = request.user
        if user.is_staff is False:
            return Response({"detail": "You don't have permissions"}, status=status.HTTP_401_UNAUTHORIZED)
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"error": "No IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
        Bid.objects.filter(id__in=ids).delete()
        return Response({"success": "Selected bids have been deleted"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def delete_bid(self, request, pk=None):
        user = request.user
        if user.is_staff is False:
            return Response({"detail": "You don't have permissions"}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            bid = Bid.objects.get(pk=pk)
            bid.delete()
            return Response({"success": "Bid has been deleted"}, status=status.HTTP_204_NO_CONTENT)
        except Bid.DoesNotExist:
            return Response({"error": "Bid not found"}, status=status.HTTP_404_NOT_FOUND)
        
class ExhibitionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    queryset = Exhibition.objects.all()
    serializer_class = ExhibitionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        try:
            if request.user is None:
                return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
            if not request.user.is_staff:
                return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response({'message': 'Success!'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if not request.user.is_staff:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({'message': 'Success!'}, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if not request.user.is_staff:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        self.perform_destroy(self.get_object())
        return Response({'message': 'Success!'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auction_request(request):
    if request.method == 'POST':
        serializer = AuctionRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            cert = compress_image(data['cert'], True)
            art = compress_image(data['art'], True)
            
            subject = 'New Auction Request'
            body = render_to_string('auction/new_request.html', {'auction': data})
            email = EmailMultiAlternatives(
                subject,
                strip_html_tags(body),
                settings.DEFAULT_FROM_EMAIL,
                [f'{settings.DEFAULT_FROM_EMAIL}']
            )
            email.attach(cert.name, cert.read(), cert.content_type)
            email.attach(art.name, art.read(), art.content_type)
            email.attach_alternative(body, "text/html")  # HTML content
            email.send()
            return Response({"message": "Auction request sent successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FaQListCreate(generics.ListCreateAPIView):
    queryset = FaQ.objects.all()
    serializer_class = FaQSerializer
    pagination_class = None
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if request.user is None:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        if request.user.is_staff is False:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer=serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FaQDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = FaQ.objects.all()
    pagination_class = None
    serializer_class = FaQSerializer
    permission_classes = [AllowAny]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        if request.user is None or not request.user.is_staff:
            return Response({'message': 'No permission'}, status=status.HTTP_401_UNAUTHORIZED)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            self.perform_update(serializer=serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({'message': 'Success!'}, status=status.HTTP_204_NO_CONTENT)
    
class AuctionWatcherViewSet(viewsets.ModelViewSet):
    queryset = AuctionWatcher.objects.all()
    serializer_class = AuctionWatcherSerializer
    permission_classes = [IsOwnerOrReadOnly, IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        return Response({'message': 'Successfully added to watching list'}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if request.user == instance.user or request.user.is_staff:
            self.perform_destroy(instance)
            return Response({'message': 'Successfully removed from watching list'}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({'error': 'You do not have permission to perform this action'}, status=status.HTTP_403_FORBIDDEN)

    def list(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'error': 'You do not have permission to view this list'}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def search(self, request):
        if request.user.is_staff:
            query = request.query_params.get('q', None)
            if query is None:
                return Response({'error': 'Query parameter "q" is required'}, status=status.HTTP_400_BAD_REQUEST)
            watchers = AuctionWatcher.objects.filter(user__username__icontains=query)
        else:
            watchers = AuctionWatcher.objects.filter(user=request.user)

        serializer = self.get_serializer(watchers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

    @action(detail=False, methods=['get'], url_path='check-notification')
    def check_notification(self, request):
        auction_id = request.query_params.get('auction_id', None)
        if auction_id is None:
            return Response({'error': 'Query parameter "auction_id" is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            watcher = AuctionWatcher.objects.get(auction_id=auction_id, user=request.user)
            return Response({'notify_via_email': watcher.notify_via_email, 'id': watcher.id}, status=status.HTTP_200_OK)
        except AuctionWatcher.DoesNotExist:
            return Response({'notify_via_email': False}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='watchers-for-auction', permission_classes=[IsAuthenticated])
    def watchers_for_auction(self, request):
        auction_id = request.query_params.get('auction_id', None)
        if auction_id is None:
            return Response({'error': 'Query parameter "auction_id" is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.is_staff:
            return Response({'error': 'You do not have permission to view this list'}, status=status.HTTP_403_FORBIDDEN)

        watchers = AuctionWatcher.objects.filter(auction_id=auction_id)
        users = [{"username": watcher.user.username, "notify_via_email": watcher.notify_via_email} for watcher in watchers]
        
        return Response(users, status=status.HTTP_200_OK)


