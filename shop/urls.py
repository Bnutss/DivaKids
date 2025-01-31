from django.urls import path
from shop.views import product_list, cart, add_to_cart, place_order, remove_from_cart

app_name = 'shop'
urlpatterns = [
    path('products/', product_list, name='product_list'),
    path('cart/', cart, name='cart'),
    path('add_to_cart/', add_to_cart, name='add_to_cart'),
    path('remove-from-cart/', remove_from_cart, name='remove_from_cart'),

    path('place_order/', place_order, name='place_order'),
]
