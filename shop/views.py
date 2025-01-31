from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.formats import localize
from .models import Product, Order, OrderItem, UserProfile, Size
import json


def product_list(request):
    if 'cart' not in request.session:
        request.session['cart'] = {}

    user_id = request.GET.get('user_id')
    if user_id and user_id.isdigit():
        request.session['user_id'] = int(user_id)

    products = Product.objects.all()
    return render(request, 'shop/product_list.html', {'products': products})


def cart(request):
    cart_items = request.session.get('cart', {})
    cart_product_ids = []
    cart_size_ids = []

    for key in cart_items.keys():
        parts = key.split('-')
        if len(parts) == 2:  # Проверяем, что ключ в формате "productID-sizeID"
            product_id, size_id = parts
            cart_product_ids.append(int(product_id))
            cart_size_ids.append(int(size_id))

    products = Product.objects.filter(id__in=cart_product_ids).prefetch_related('sizes')
    sizes = {size.id: size for size in Size.objects.filter(id__in=cart_size_ids)}

    total_price = 0
    cart_display = []

    for key, quantity in cart_items.items():
        parts = key.split('-')
        product_id = int(parts[0])
        size_id = int(parts[1]) if len(parts) == 2 else None

        product = next((p for p in products if p.id == product_id), None)
        size = sizes.get(size_id) if size_id else None

        if product:
            total_price += product.price * quantity
            cart_display.append({
                'product': product,
                'size': size.size if size else "Без размера",
                'quantity': quantity,
                'subtotal': product.price * quantity
            })

    formatted_total_price = localize(total_price)
    user_id = request.session.get('user_id')

    return render(request, 'shop/cart.html', {
        'cart_items': cart_display,
        'total_price': formatted_total_price,
        'user_id': user_id
    })


@csrf_exempt
def add_to_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            size_id = str(data.get('size_id'))
            quantity = int(data.get('quantity', 1))

            # Проверка, что product_id и size_id являются числами
            if not product_id.isdigit() or not size_id.isdigit():
                return JsonResponse({'status': 'error', 'message': 'Некорректный ID товара или размера'}, status=400)

            # Проверка существования товара и размера
            product = Product.objects.filter(id=product_id).first()
            size = Size.objects.filter(id=size_id).first()

            if not product:
                return JsonResponse({'status': 'error', 'message': 'Товар не найден'}, status=404)
            if not size:
                return JsonResponse({'status': 'error', 'message': 'Размер не найден'}, status=404)

            # Проверка, что размер доступен для данного товара
            if size not in product.sizes.all():
                return JsonResponse({'status': 'error', 'message': 'Этот размер недоступен для данного товара'},
                                    status=400)

            cart = request.session.get('cart', {})
            cart_key = f"{product_id}-{size_id}"  # Формат ключа: "productID-sizeID"

            if cart_key in cart:
                cart[cart_key] += quantity
                if cart[cart_key] <= 0:
                    del cart[cart_key]
            else:
                if quantity > 0:
                    cart[cart_key] = quantity

            request.session['cart'] = cart

            # Пересчет общей стоимости корзины
            total_price = sum(
                Product.objects.get(id=int(pid.split('-')[0])).price * qty for pid, qty in cart.items()
            )
            formatted_total_price = f"{total_price:,}".replace(",", " ")

            return JsonResponse({'status': 'success', 'total_price': formatted_total_price})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Неверный метод запроса.'})

    user_id = request.POST.get('user_id') or request.session.get('user_id')
    if not user_id or not str(user_id).isdigit():
        return JsonResponse({'success': False, 'message': 'Некорректный user_id.'})

    user_id = int(user_id)
    try:
        user_profile = UserProfile.objects.get(user_id=user_id)
        name = user_profile.name or request.POST.get('name')
        phone_number = user_profile.phone_number or request.POST.get('phone_number')
        address = user_profile.delivery_address or request.POST.get('address')
    except UserProfile.DoesNotExist:
        name = request.POST.get('name')
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')

    if not all([name, phone_number, address]):
        return JsonResponse({'success': False, 'message': 'Не удалось получить полные данные пользователя.'})

    cart_items = request.session.get('cart', {})
    if not cart_items:
        return JsonResponse({'success': False, 'message': 'Ваша корзина пуста.'})

    comment = request.POST.get('comment', '')

    try:
        order = Order.objects.create(
            user_id=user_id,
            name=name,
            phone_number=phone_number,
            address=address,
            comment=comment,
        )

        for key, quantity in cart_items.items():
            parts = key.split('-')
            product_id = int(parts[0])
            size_id = int(parts[1]) if len(parts) == 2 else None

            product = get_object_or_404(Product, id=product_id)
            size = get_object_or_404(Size, id=size_id) if size_id else None

            OrderItem.objects.create(order=order, product=product, size=size, quantity=quantity)

        order.calculate_total_price()
        request.session['cart'] = {}
        return JsonResponse({'success': True, 'message': 'Заказ успешно оформлен!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Ошибка при оформлении заказа: {e}'})


@csrf_exempt
def remove_from_cart(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            size_id = str(data.get('size_id'))

            if not product_id.isdigit() or not size_id.isdigit():
                return JsonResponse({'status': 'error', 'message': 'Некорректный ID товара или размера'}, status=400)

            cart = request.session.get('cart', {})
            cart_key = f"{product_id}-{size_id}"

            if cart_key in cart:
                del cart[cart_key]

            request.session['cart'] = cart

            total_price = sum(
                Product.objects.get(id=int(pid.split('-')[0])).price * qty for pid, qty in cart.items()
            )
            formatted_total_price = f"{total_price:,}".replace(",", " ")

            return JsonResponse({
                'status': 'success',
                'total_price': formatted_total_price,
                'cart_empty': len(cart) == 0
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
