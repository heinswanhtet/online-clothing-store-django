from django.conf import settings
from django.db import models
from django.shortcuts import reverse
from django.db.models.signals import pre_save, post_save
from django_countries.fields import CountryField

# Create your models here.

CATEGORY_CHOICE = (
    ('Shirt', 'Shirt'),
    ('Pant', 'Pant'),
    ('T-Shirt', 'T-Shirt'),
)

LABEL_CHOICE = (
    ('P', 'primary'),
    ('S', 'secondary'),
    ('D', 'danger')
)

ADDRESS_CHOICE = (
    ('S', 'Shipping Address'),
    ('B', 'Billing Address'),
)

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Item(models.Model):
    title = models.CharField(max_length=50)
    price = models.IntegerField(default=0)
    discount_price = models.IntegerField(blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICE)
    label = models.CharField(max_length=50, choices=LABEL_CHOICE, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('mysite:product', kwargs={ 'slug': self.slug })
    
    def add_to_cart(self):
        return reverse('mysite:add-to-cart', kwargs={ 'slug': self.slug })
    
    def remove_from_cart(self):
        return reverse('mysite:remove-from-cart', kwargs={ 'slug': self.slug })
    
    def increase_quantity(self):
        return reverse('mysite:increase-quantity', kwargs={ 'slug': self.slug })
    
    def decrease_quantity(self):
        return reverse('mysite:decrease-quantity', kwargs={ 'slug': self.slug })
    
    def remove_item(self):
        return reverse('mysite:remove', kwargs={ 'slug': self.slug })

class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    ordered = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.quantity} of {self.item.title}'
    
    def calculate_total_price(self):
        return self.item.price * self.quantity
    
    def calculate_total_discount_price(self):
        return self.item.discount_price * self.quantity
    
    def calculate_amount_saved(self):
        return self.calculate_total_price() - self.calculate_total_discount_price()
    
    def get_order_item_total_price(self):
        if self.item.discount_price:
            return self.calculate_total_discount_price()
        return self.calculate_total_price()
    
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    refrence_key = models.CharField(max_length=20, blank=True, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    shipping_address = models.ForeignKey('Address', related_name='shipping_address', on_delete=models.SET_NULL, blank=True, null=True)
    billing_address = models.ForeignKey('Address', related_name='billing_address', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey('Payment', on_delete=models.SET_NULL, blank=True, null=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, blank=True, null=True)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)


    def __str__(self):
        return self.user.username
    
    def calculate_order_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_order_item_total_price()
        if self.coupon:
            total -= self.coupon.amount
        return total

class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICE)
    default = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return self.user.username

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=50)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

class Coupon(models.Model):
    code = models.CharField(max_length=25)
    amount = models.IntegerField()

    def __str__(self):
        return self.code
    
class Refund(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    email = models.EmailField()
    reason = models.TextField()
    order = models.OneToOneField(Order, on_delete=models.CASCADE, blank=True, null=True, related_name='refund')
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.email}'

def pre_item_create_slug_signal(sender, instance, *args, **kwargs):
    instance.slug = f'{instance.category.lower()}-{instance.title}'

def post_user_profile_create_signal(sender, instance, created, *args, **kwargs):
    if created:
        UserProfile.objects.create(user=isinstance)

pre_save.connect(pre_item_create_slug_signal, sender=Item)
post_save.connect(post_user_profile_create_signal, sender=settings.AUTH_USER_MODEL)