from django.urls import path

from . import views

app_name = 'mysite'

urlpatterns = [
    path('', views.ItemListView.as_view(), name='home'),
    path('product/<slug>/', views.ItemDetailView.as_view(), name='product'),

    path('add-to-cart/<slug>/', views.addItemToCart, name='add-to-cart'),
    path('remove-from-cart/<slug>/', views.removeItemFromCart, name='remove-from-cart'),

    path('increase-quantity/<slug>/', views.increaseQuantity, name='increase-quantity'),
    path('decrease-quantity/<slug>/', views.decreaseQuantity, name='decrease-quantity'),
    path('remove/<slug>/', views.removeItem, name='remove'),


    path('order-summary/', views.OrderSummaryView.as_view(), name='order-summary'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('payment/<payment_option>/', views.PaymentView.as_view(), name='payment'),
    path('add-coupon/', views.AddCounponView.as_view(), name='add-coupon'),
    path('refund/', views.CreateRefundView.as_view(), name='refund'),
]
