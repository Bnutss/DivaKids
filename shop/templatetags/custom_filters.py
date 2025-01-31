from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(str(key), 0)
    return 0


@register.filter
def calculate_total(cart, products):
    total = 0
    for product in products:
        if str(product.id) in cart:
            total += product.price * cart[str(product.id)]
    return int(total)
