from django.contrib import admin

from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile

# Register your models here.

def make_refund_accepted(modeladmin, request, queryset):
    # queryset.update(refund_requested=False, refund_granted=True)
    for order in queryset:
        if order.refund_requested:
            order.refund_requested=False
            order.refund_granted=True
            order.refund.accepted = True
            order.refund.save()
            order.save()

make_refund_accepted.short_description = 'Update orders to refund granted'    

class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'country',
        'address_type',
        'default'
    ]

class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'ordered', 'being_delivered', 'received', 'refund_requested', 'refund_granted', 'shipping_address','billing_address', 'payment', 'coupon'
    ]
    list_display_links = ['user', 'shipping_address', 'billing_address', 'payment', 'coupon']
    list_editable = ('being_delivered', 'received',)
    list_filter = ['ordered', 'being_delivered', 'received', 'refund_requested', 'refund_granted']
    search_fields = ['user__username',]
    actions = [make_refund_accepted,]

class RefundAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'accepted'
    ]

admin.site.register(UserProfile)
admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order, OrderAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Payment)
admin.site.register(Coupon)
admin.site.register(Refund, RefundAdmin)
