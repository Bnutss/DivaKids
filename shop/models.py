import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image
from django.db import models
from django.utils import timezone


class Size(models.Model):
    size = models.CharField(max_length=10, verbose_name='Размер')

    def __str__(self):
        return self.size

    class Meta:
        verbose_name = 'Размер'
        verbose_name_plural = 'Размеры'


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    sizes = models.ManyToManyField('Size', verbose_name='Размеры', blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена за единицу')

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='Продукт')
    image = models.ImageField(upload_to='products/', verbose_name='Фото')

    def save(self, *args, **kwargs):
        if self.image:
            try:
                ext = os.path.splitext(self.image.name)[-1].lower()
                if ext != '.webp':
                    img = Image.open(self.image)
                    img = img.convert('RGB')
                    output = BytesIO()
                    img.save(output, format='WEBP', quality=85)
                    output.seek(0)

                    new_name = f"{os.path.splitext(self.image.name)[0]}.webp"
                    self.image = ContentFile(output.read(), new_name)
            except Exception as e:
                print(f"Ошибка при обработке изображения: {e}")

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Изображение продукта'
        verbose_name_plural = 'Изображения продуктов'


class Order(models.Model):
    """Модель заказа."""
    user_id = models.BigIntegerField(verbose_name='ID пользователя в Telegram')
    name = models.CharField(max_length=255, verbose_name='Имя заказчика', blank=True, null=True)
    phone_number = models.CharField(max_length=15, verbose_name='Мобильный номер', blank=True, null=True)
    address = models.TextField(verbose_name='Адрес доставки', blank=True, null=True)
    products = models.ManyToManyField('Product', through='OrderItem', verbose_name='Продукты')
    comment = models.TextField(verbose_name='Комментарий к заказу', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Общая цена', default=0)
    is_confirmed = models.BooleanField(verbose_name='Подтвержденный', default=False)
    confirmed_at = models.DateTimeField(verbose_name='Дата подтверждения', blank=True, null=True)
    is_rejected = models.BooleanField(verbose_name='Отклоненный', default=False)
    rejected_at = models.DateTimeField(verbose_name='Дата отклонения', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_confirmed and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        if self.is_rejected and not self.rejected_at:
            self.rejected_at = timezone.now()
        super().save(*args, **kwargs)

    def calculate_total_price(self):
        """
        Рассчитывает общую стоимость заказа на основе связанных товаров.
        """
        self.total_price = sum(
            item.quantity * item.product.price
            for item in self.orderitem_set.all()
        )
        self.save()

    def __str__(self):
        return f"Заказ #{self.id} от {self.name or 'Неизвестного пользователя'}"

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class OrderItem(models.Model):
    """Промежуточная модель для связи товаров с заказами."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='Продукт')
    size = models.ForeignKey('Size', on_delete=models.SET_NULL, verbose_name='Размер', null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    def __str__(self):
        size_info = f" | Размер: {self.size}" if self.size else ""
        return f"{self.product.name} (x{self.quantity}){size_info}"

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'


class UserProfile(models.Model):
    user_id = models.BigIntegerField(unique=True, verbose_name="Telegram-ID")
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Имя")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Номер телефона")
    delivery_address = models.TextField(blank=True, null=True, verbose_name="Адрес доставки")

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль {self.user_id}"
