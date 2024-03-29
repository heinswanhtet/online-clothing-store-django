from django.shortcuts import render, get_object_or_404, reverse, redirect
from django.views import generic
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q

from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile
from .forms import CheckOutForm, CouponForm, RefundForm, PaymentForm

import stripe, random, string

# Create your views here.

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_refrence_key():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def search_Item(query, qs, context):
    qs = qs.filter(
        Q(title__icontains=query) |
        Q(category__icontains=query)
    )
    context.update({
        'items': qs
    })

class ItemListView(generic.ListView):
    template_name = 'shopping/home-page.html'
    context_object_name = 'items'
    paginate_by = 8

    def get_queryset(self):
        return Item.objects.order_by('-price')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('search')
        if query:
            qs = self.get_queryset()
            search_Item(query, qs, context)
        return context
    
class ItemDetailView(generic.DetailView):
    template_name = 'shopping/product-page.html'
    context_object_name = 'item'

    def get_queryset(self):
        return Item.objects.all()
    
class OrderSummaryView(LoginRequiredMixin, generic.View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'order': order
            }
            return render(self.request, 'shopping/summary-page.html' ,context) 
        except ObjectDoesNotExist:
            messages.info(self.request, 'You do not have active order.')
            return render(self.request, 'shopping/summary-page.html') 
            
        
# class OrderSummaryView(generic.ListView):
#     template_name = 'shopping/summary-page.html'
#     context_object_name = 'order'

#     def get_queryset(self):
#         return Order.objects.filter(user=self.request.user, ordered=False)

class CheckoutView(generic.View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckOutForm
            if order.billing_address:
                return redirect('mysite:payment', payment_option='stripe')
            context = {
                'order': order,
                'form': form,
                'coupon_form': CouponForm(),
                'show_promo_code_section': True if not order.coupon else False,
            }

            shipping_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )
            if shipping_address_qs.exists():
                context.update({
                    'shipping_address_default': shipping_address_qs[len(shipping_address_qs)-1]
                })

            billing_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'B',
                default = True
            )
            if billing_address_qs.exists():
                context.update({
                    'billing_address_default': billing_address_qs[len(billing_address_qs)-1]
                })

            return render(self.request, 'shopping/checkout-page.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, 'You do not have active order.')
            return redirect('mysite:home')
    
    def post(self, *args, **kwargs):
        form = CheckOutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                # print(form.cleaned_data)

                use_default_shipping = form.cleaned_data.get('use_default_shipping')

                if use_default_shipping:
                    shipping_address_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'S',
                        default = True
                    )
                    order.shipping_address = shipping_address_qs[len(shipping_address_qs)-1]
                    order.save()
                else:
                    print('User is entering a new shipping addresss')
                    shipping_address_1 = form.cleaned_data.get('shipping_address_1') 
                    shipping_address_2 = form.cleaned_data.get('shipping_address_2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zipcode = form.cleaned_data.get('shipping_zipcode')
                    set_default_shipping = form.cleaned_data.get('set_default_shipping')

                    if self.is_valid_form([shipping_address_1, shipping_country, shipping_zipcode]):
                        shipping_address = Address()
                        shipping_address.user = self.request.user
                        shipping_address.street_address = shipping_address_1
                        shipping_address.apartment_address = shipping_address_2
                        shipping_address.zipcode = shipping_zipcode
                        shipping_address.country = shipping_country
                        shipping_address.address_type = 'S'
                        shipping_address.default = set_default_shipping
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(self.request, 'Please fill in the required shipping address fields')
                        return redirect('mysite:checkout')
                    
                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing = form.cleaned_data.get('same_billing_address')

                if same_billing:
                    billing_address = order.shipping_address
                    billing_address.pk = None
                    billing_address.save()

                    billing_address.address_type = 'B'
                    billing_address.save()

                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    billing_address_qs = Address.objects.filter(
                        user = self.request.user,
                        address_type = 'B',
                        default = True
                    )
                    order.billing_address = billing_address_qs[len(billing_address_qs)-1]
                    order.save()
                else:
                    print('User is entering a new billing addresss')
                    billing_address_1 = form.cleaned_data.get('billing_address_1') 
                    billing_address_2 = form.cleaned_data.get('billing_address_2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zipcode = form.cleaned_data.get('billing_zipcode')
                    set_default_billing = form.cleaned_data.get('set_default_billing')

                    if self.is_valid_form([billing_address_1, billing_country, billing_zipcode]):
                        billing_address = Address()
                        billing_address.user = self.request.user
                        billing_address.street_address = billing_address_1
                        billing_address.apartment_address = billing_address_2
                        billing_address.zipcode = billing_zipcode
                        billing_address.country = billing_country
                        billing_address.address_type = 'B'
                        billing_address.default = set_default_billing
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request, 'Please fill in the required billing address fields')
                        return redirect('mysite:checkout')


                payment_option = form.cleaned_data.get('payment_options')

                # order.ordered = True
                # order.save()
                if payment_option == 'S':
                    return redirect('mysite:payment', payment_option='stripe')
                if payment_option == 'P':
                    return redirect('mysite:payment', payment_option='paypal')

                # messages.info(self.request, 'Checkout success')
                # return redirect('mysite:home')
            
            messages.warning(self.request, 'Failed checkout')
            return redirect('mysite:checkout')
        
        except ObjectDoesNotExist:
            messages.info(self.request, 'You do not have active order.')
            return render(self.request, 'shopping/summary-page.html') 
        
    def is_valid_form(self, addresses):
        for address in addresses:
            if address == '':
                return False
        return True
        
class PaymentView(generic.View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if not order.billing_address:
            return redirect('mysite:checkout')
        context = {
            'order': order,
            'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
            'show_promo_code_section': False,
        }
        userprofile = self.request.user.userprofile
        if userprofile.one_click_purchasing:
            cards = stripe.Customer.list_sources(
                userprofile.stripe_customer_id,
                limit=3,
                object='card'
            )
            # print(cards)
            card_list = cards['data']
            if len(card_list) > 0:
                context.update({
                    'card': card_list[0] if len(card_list) == 1 else card_list[1]
                })
        return render(self.request, 'shopping/payment.html', context)

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        # token = self.request.POST.get('stripeToken')
        userprofile = UserProfile.objects.get(user=self.request.user)
        form = PaymentForm(self.request.POST)

        if form.is_valid():
            # print(form.cleaned_data)
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            user_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    # customer = stripe.Customer.retrieve(userprofile.stripe_customer_id)
                    # customer.sources.create(source=token)
                    customer = stripe.Customer.create_source(
                        userprofile.stripe_customer_id,
                        source=token
                    )
                else:
                    # customer = stripe.Customer.create(email=self.request.user.email)
                    # customer.sources.create(source=token)
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                        source=token
                    )
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.calculate_order_total() * 100)

            try:
                if user_default or save:
                    charge = stripe.Charge.create(
                        amount = amount,
                        currency = 'usd',
                        customer = userprofile.stripe_customer_id
                    )
                else:
                    charge = stripe.Charge.create(
                        amount = amount,
                        currency = 'usd',
                        source = token
                    )

                payment = Payment()
                payment.user = self.request.user
                payment.stripe_charge_id = charge['id']
                payment.amount = order.calculate_order_total()
                payment.save()

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.refrence_key = create_refrence_key()
                order.save()

                send_mail(
                    subject='Yo!',
                    message=f'Purchased successfully. Your refrence code for the order is {order.refrence_key}. Please use that key to refund your order.',
                    from_email='admin-luffy@hello.com',
                    recipient_list=[self.request.user.email]
                )

                messages.success(self.request, "Your order was successful and please check your email for the detail")
                return redirect('mysite:home')
            
            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.error(self.request, f"{err.get('message')}")
            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.success(self.request, "Rate limit error")
                return redirect("/")
            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                messages.success(self.request, "Invalid parameters")
                return redirect("/")
            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.success(self.request, "Not authenticated")
                return redirect("/")
            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.success(self.request, "Newtwork error")
                return redirect("/")
            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.success(
                    self.request, "Something went wrong. You were not charged. Please try again")
                return redirect("/")
            except Exception as e:
                # Something else happened, completely unrelated to Stripe
                messages.success(
                    self.request, "A serious error occured. We have been notified.")
                return redirect("/")

        messages.warning(self.request, 'Invalid data received')
        return redirect('mysite:payment', payment_option='stripe')

class AddCounponView(generic.View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                order = Order.objects.get(user=self.request.user, ordered=False)
                coupon = self.get_coupon(form.cleaned_data['coupon_code'])
                if coupon: 
                    order.coupon = coupon 
                else:
                    messages.info(self.request, 'Invalid Coupon Code')
                    return redirect('mysite:checkout')
                order.save()
                messages.info(self.request, 'Successfully added cupon code')
                return redirect('mysite:payment', payment_option='stripe')
            except ObjectDoesNotExist:
                messages.info(self.request, 'You do not have active order.')
                return redirect('mysite:order-summary')
        
        return None
    
    def get_coupon(self, input_coupon):
        try:
            coupon = Coupon.objects.get(code=input_coupon)
            return coupon
        except ObjectDoesNotExist:
            return None

class CreateRefundView(generic.View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, 'shopping/refund.html', context)
    
    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST or None)
        if form.is_valid():
            ref_code = form.cleaned_data.get('refrence_key')
            email = form.cleaned_data.get('email')
            reason = form.cleaned_data.get('reason')
            try:
                order = Order.objects.get(refrence_key = ref_code)
                refund = Refund()
                refund.user = self.request.user
                refund.email = email
                refund.reason = reason
                refund.order = order
                refund.save()
                order.refund_requested = True
                order.save()
                messages.info(self.request, 'Refund is requested')
                return redirect('mysite:refund')
            except ObjectDoesNotExist:
                messages.warning(self.request, 'Invalid Refrence Key')
                return redirect('mysite:refund')


@login_required
def addItemToCart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
        user = request.user,
        item = item,
        ordered = False
    )
    order_qs = Order.objects.filter(user = request.user, ordered = False)
    # print(order_qs)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item.quantity += 1
            ordered_item.save()
            messages.info(request, f'The quantity of {item.title} is updated.')
        else:
            order.items.add(ordered_item)
            messages.info(request, f'{item.title} is addded to your cart.')
        return redirect('mysite:product', slug=slug)
    else:
        order = Order.objects.create(
            user = request.user, 
            ordered_date = timezone.now(), 
            ordered = False
        )
        order.items.add(ordered_item)
        messages.info(request, f'{item.title} is addded to your cart.')
        return redirect('mysite:product', slug=slug)

@login_required    
def removeItemFromCart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
        user = request.user,
        item = item,
        ordered = False
    )
    order_qs = Order.objects.filter(user = request.user, ordered = False)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item.delete()
            messages.info(request, f'{item.title} is removed from your cart.')
            if not order.items.count():
                order.delete()
                messages.info(request, 'You have no active order.')    
            return redirect('mysite:product', slug=slug)
        else:
            messages.info(request, f'{item.title} is not from your cart.')
            return redirect('mysite:product', slug=slug)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect('mysite:product', slug=slug)
    
@login_required
def increaseQuantity(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
        user = request.user,
        item = item,
        ordered = False
    )
    order_qs = Order.objects.filter(user = request.user, ordered = False)
    # print(order_qs)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item.quantity += 1
            ordered_item.save()
            messages.info(request, f'The quantity of {item.title} is updated.')
        else:
            order.items.add(ordered_item)
            messages.info(request, f'{item.title} is addded to your cart.')
        return redirect('mysite:order-summary')
    else:
        order = Order.objects.create(
            user = request.user, 
            ordered_date = timezone.now(), 
            ordered = False
        )
        order.items.add(ordered_item)
        messages.info(request, f'{item.title} is addded to your cart.')
        return redirect('mysite:order-summary')

@login_required
def decreaseQuantity(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
        user = request.user,
        item = item,
        ordered = False
    )
    order_qs = Order.objects.filter(user = request.user, ordered = False)
    # print(order_qs)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item.quantity -= 1
            ordered_item.save()
            if not ordered_item.quantity:
                ordered_item.delete()
                if not order.items.exists():
                    order.delete()
                return redirect('mysite:order-summary')
            messages.info(request, f'The quantity of {item.title} is updated.')
            return redirect('mysite:order-summary')
        else:
            messages.info(request, f'{item.title} is not from your cart.')
            return redirect('mysite:order-summary')
    else:
        messages.info(request, "You do not have an active order.")
        return redirect('mysite:order-summary')
    
@login_required    
def removeItem(request, slug):
    item = get_object_or_404(Item, slug=slug)
    ordered_item, created = OrderItem.objects.get_or_create(
        user = request.user,
        item = item,
        ordered = False
    )
    order_qs = Order.objects.filter(user = request.user, ordered = False)

    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            ordered_item.delete()
            messages.info(request, f'{item.title} is removed from your cart.')
            if not order.items.exists():
                order.delete()
                # messages.info(request, 'You have no active order.')    
                
            return redirect('mysite:order-summary')
        else:
            messages.info(request, f'{item.title} is not from your cart.')
            return redirect('mysite:product', slug=slug)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect('mysite:product', slug=slug)
    