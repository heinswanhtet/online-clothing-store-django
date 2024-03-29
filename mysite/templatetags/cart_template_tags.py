from django import template
from mysite.models import Order

register = template.Library()

@register.filter
def cart_item_count(user):
    qs = Order.objects.filter(user=user, ordered=False)
    if qs.exists():
        # print(qs[0].items.all())
        return qs[0].items.count()
    return 0