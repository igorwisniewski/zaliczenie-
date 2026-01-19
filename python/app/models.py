from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Auction(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Tytul'))
    artist = models.CharField(max_length=200, verbose_name=_('Artysta'))
    year = models.IntegerField(verbose_name=_('Rok'))
    medium = models.CharField(max_length=200, verbose_name=_('Technika'))
    dimensions = models.CharField(max_length=200, verbose_name=_('Wymiary'))
    description = models.TextField(verbose_name=_('Opis'))
    image = models.ImageField(upload_to='auction_images/', default='default.jpg', verbose_name=_('Zdjecie'))
    current_bid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Aktualna oferta'))
    end_date = models.DateTimeField(verbose_name=_('Data zakonczenia'))
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Cena kup teraz'), blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.buy_now_price is None:
            self.buy_now_price = self.current_bid * 3
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Aukcja')
        verbose_name_plural = _('Aukcje')
        ordering = ['id']


class Item(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Tytul'))
    artist = models.CharField(max_length=200, verbose_name=_('Artysta'))
    year = models.IntegerField(verbose_name=_('Rok'))
    medium = models.CharField(max_length=200, verbose_name=_('Technika'))
    dimensions = models.CharField(max_length=200, verbose_name=_('Wymiary'))
    description = models.TextField(verbose_name=_('Opis'))
    image = models.ImageField(upload_to='items_images/', default='default.jpg', verbose_name=_('Zdjecie'))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Cena kup teraz'))
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, default=None, related_name="buyer")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Data utworzenia'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Data aktualizacji'))

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Przedmiot')
        verbose_name_plural = _('Przedmioty')
        ordering = ['id']

class Bid(models.Model):
    auction = models.ForeignKey(Auction, related_name='bids', on_delete=models.CASCADE, verbose_name=_('Aukcja'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('UÅ¼ytkownik'))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Kwota'))
    date = models.DateTimeField(auto_now_add=True, verbose_name=_('Data'))

    def __str__(self):
        return f'{self.user.username} - {self.amount}'

    class Meta:
        verbose_name = _('Oferta')
        verbose_name_plural = _('Oferty')
        ordering = ['id']


class AuctionWatcher(models.Model):
    auction = models.ForeignKey(Auction, related_name='watchers', on_delete=models.CASCADE, verbose_name=_('Aukcja'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_('Użytkownik'))
    notify_via_email = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']


class Section(models.Model):
    title = models.CharField(max_length=75, verbose_name=_('TytuÅ‚'))
    title2 = models.CharField(max_length=75, default=None, null=True, blank=True, verbose_name=_('TytuÅ‚ 2'))
    text = models.TextField(max_length=5000, default=None, blank=True, verbose_name=_('Tekst'))
    element1 = models.TextField(max_length=650, default=None, blank=True, null=True, verbose_name=_('Element 1'))
    element2 = models.TextField(max_length=650, default=None, blank=True, null=True, verbose_name=_('Element 2'))
    element3 = models.TextField(max_length=650, default=None, blank=True, null=True, verbose_name=_('Element 3'))
    element4 = models.TextField(max_length=650, default=None, blank=True, null=True, verbose_name=_('Element 4'))
    image1 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)
    image2 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)
    image3 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)
    image4 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)
    image5 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)
    image6 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)
    image7 = models.ImageField(upload_to='gallery_images/', verbose_name=_('Zdjecie'), blank=True, null=True)


    class Meta:
        verbose_name = _('Sekcja')
        verbose_name_plural = _('Sekcje')
        ordering = ['id']


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Nazwa"))

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Kategoria')
        verbose_name_plural = _('Kategorie')
        ordering = ['id']

class GalleryItem(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('TytuÅ‚'))
    artist = models.CharField(max_length=200, verbose_name=_('Artysta'))
    description = models.TextField(verbose_name=_('Opis'))
    image = models.ImageField(upload_to='gallery_images/', verbose_name=_('ZdjÄ™cie'))
    categories = models.ManyToManyField(Category, related_name='gallery_items', verbose_name=_('Kategorie'), blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Galeria')
        verbose_name_plural = _('Galerie')
        ordering = ['id']

class Exhibition(models.Model):
    title = models.CharField(max_length=200,blank=True, null=True)
    title2 = models.CharField(max_length=200,blank=True, null=True)
    title3 = models.CharField(max_length=200,blank=True, null=True)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    link = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='exhibitions/', blank=True, null=True)
    element1 = models.TextField(max_length=20000,blank=True, null=True)
    element2 = models.TextField(max_length=20000,blank=True, null=True)
    element3 = models.TextField(max_length=20000,blank=True, null=True)
    element4 = models.TextField(max_length=20000,blank=True, null=True)

    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['id']
    

class FaQ(models.Model):
    question = models.CharField(max_length=2000)
    answer = models.CharField(max_length=2000)

    def __str__(self) -> str:
        return self.question
    
    class Meta:
        ordering = ['id']

class NotificationLog(models.Model):
    user_email = models.EmailField(db_index=True)
    auction_id = models.PositiveIntegerField(db_index=True)
    last_notified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user_email', 'auction_id')
        indexes = [
            models.Index(fields=['user_email']),
            models.Index(fields=['auction_id']),
            models.Index(fields=['last_notified_at']),
        ]
