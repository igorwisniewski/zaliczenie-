from django.utils import timezone
from rest_framework import serializers
from .models import Auction, AuctionWatcher, Bid, Category, Exhibition, FaQ, GalleryItem, Item, Section
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class AuctionSerializerWithStatus(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = '__all__'
        extra_kwargs = {
            'buy_now_price': {'required': False, 'allow_null': True}
        }

    def get_status(self, obj):
        bid = self.context.get('bid')
        if bid:
            if obj.current_bid == bid.amount and obj.end_date < timezone.now():
                return 'wygrane'
            elif obj.end_date > timezone.now():
                return 'trwające'
            else:
                return 'zakończone'
        return 'zakończone'

class BidSerializer(serializers.ModelSerializer):

    auction = AuctionSerializerWithStatus()

    class Meta:
        model = Bid
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['auction'] = AuctionSerializerWithStatus(instance.auction, context={'bid': instance}).data
        return representation

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'


class AuctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = '__all__'
        extra_kwargs = {
            'buy_now_price': {'required': False, 'allow_null': True},
        }

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'
        extra_kwargs = {
            'buyer': {'required': False, 'allow_null': True},
        }

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

class ItemSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True},
            'buyer': {'required': False, 'allow_null': True},
        }

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class AuctionSerializerUpdate(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = '__all__'
        extra_kwargs = {
            'image': {'required': False, 'allow_null': True}
        }


class SendEmailSerializer(serializers.Serializer):
    firstName = serializers.CharField(min_length=4, max_length=50)
    lastName = serializers.CharField(min_length=4, max_length=50)
    email = serializers.EmailField()
    text = serializers.CharField(min_length=2, max_length=4000)


class GalleryItemSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField()

    class Meta:
        model = GalleryItem
        fields = '__all__'

    def get_categories(self, obj):
        return [category.name.strip() for category in obj.categories.all()]

    def update(self, instance, validated_data):
        categories_data = validated_data.pop('categories', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if categories_data is not None:
            categories = Category.objects.filter(name__in=categories_data)
            instance.categories.set(categories)
        
        instance.save()
        return instance



class ExhibitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exhibition
        fields = '__all__'


class AuctionRequestSerializer(serializers.Serializer):
    firstName = serializers.CharField(min_length=4, max_length=50)
    lastName = serializers.CharField(min_length=4, max_length=50)
    email = serializers.EmailField()
    message = serializers.CharField(min_length=2, max_length=4000)
    art = serializers.ImageField()
    cert = serializers.ImageField()

class FaQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaQ
        fields = '__all__'

class AuctionWatcherSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuctionWatcher
        fields = ['id', 'auction', 'user', 'notify_via_email']
        read_only_fields = ['user']