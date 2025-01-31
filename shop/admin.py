from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from shop.models import Product, ProductImage, Order, OrderItem, UserProfile, Size


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    """Админ-панель для управления размерами."""
    list_display = ('size',)
    search_fields = ('size',)


class ProductImageInline(admin.TabularInline):
    """Инлайн-форма для добавления нескольких изображений к продукту."""
    model = ProductImage
    extra = 1
    fields = ('image', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        """Предпросмотр изображения."""
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />')
        return "Нет изображения"

    image_preview.short_description = "Предпросмотр"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Админ-панель для управления продуктами."""

    list_display = ('name', 'price')
    search_fields = ('name', 'description')
    list_filter = ('price',)
    list_editable = ('price',)
    fields = ('name', 'description', 'price', 'sizes')
    filter_horizontal = ('sizes',)
    inlines = [ProductImageInline]


class OrderItemInline(admin.TabularInline):
    """Встроенная админ-панель для элементов заказа."""
    model = OrderItem
    extra = 1
    readonly_fields = ('item_total', 'size_display')
    fields = ('product', 'size_display', 'quantity', 'item_total')

    def size_display(self, obj):
        """Отображает размер продукта, если он есть."""
        return obj.size.size if obj.size else "Без размера"

    size_display.short_description = 'Размер'

    def item_total(self, obj):
        """Рассчитывает общую стоимость элемента заказа."""
        return obj.quantity * obj.product.price if obj.product else 0

    item_total.short_description = 'Общая стоимость'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админ-панель для управления заказами."""

    list_display = ('id', 'user_id', 'name', 'phone_number', 'total_price', 'is_confirmed', 'is_rejected', 'created_at')
    list_filter = ('created_at', 'is_confirmed', 'is_rejected')
    search_fields = ('user_id', 'name', 'phone_number', 'address')
    ordering = ('-created_at',)
    readonly_fields = ('total_price', 'created_at', 'confirmed_at', 'rejected_at')
    list_editable = ('is_confirmed', 'is_rejected')
    fieldsets = (
        ('Основная информация', {
            'fields': ('user_id', 'name', 'phone_number', 'address', 'comment'),
        }),
        ('Статусы', {
            'fields': ('is_confirmed', 'confirmed_at', 'is_rejected', 'rejected_at'),
        }),
        ('Дополнительно', {
            'fields': ('total_price', 'created_at'),
        }),
    )
    inlines = [OrderItemInline]
    actions = ['mark_as_confirmed', 'mark_as_rejected']

    def save_model(self, request, obj, form, change):
        """Переопределяет сохранение заказа, чтобы пересчитать общую стоимость и обновить даты."""
        if obj.is_confirmed and not obj.confirmed_at:
            obj.confirmed_at = now()
        if obj.is_rejected and not obj.rejected_at:
            obj.rejected_at = now()
        super().save_model(request, obj, form, change)
        obj.calculate_total_price()

    @admin.action(description='Подтвердить выбранные заказы')
    def mark_as_confirmed(self, request, queryset):
        """Массовое действие: подтвердить выбранные заказы."""
        queryset.update(is_confirmed=True, confirmed_at=now())
        self.message_user(request, 'Выбранные заказы подтверждены.')

    @admin.action(description='Отклонить выбранные заказы')
    def mark_as_rejected(self, request, queryset):
        """Массовое действие: отклонить выбранные заказы."""
        queryset.update(is_rejected=True, rejected_at=now())
        self.message_user(request, 'Выбранные заказы отклонены.')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Админ-панель для управления элементами заказа."""

    list_display = ('order', 'product', 'quantity', 'size_display', 'item_total')
    search_fields = ('order__id', 'product__name', 'size__name')
    list_filter = ('order', 'product', 'size')
    readonly_fields = ('size_display',)  # Добавил в readonly_fields

    def size_display(self, obj):
        """Отображает размер продукта, если он есть, иначе показывает 'Без размера'."""
        return obj.size.size if obj.size else "Без размера"

    size_display.short_description = 'Размер'

    def item_total(self, obj):
        """Рассчитывает общую стоимость элемента заказа."""
        return obj.quantity * obj.product.price

    item_total.short_description = 'Общая стоимость'

    def save_model(self, request, obj, form, change):
        """Переопределяет сохранение элемента заказа, чтобы пересчитать общую стоимость заказа."""
        super().save_model(request, obj, form, change)
        obj.order.calculate_total_price()


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Админ-панель для управления профилями пользователей."""

    list_display = ("user_id", "name", "phone_number", "delivery_address")
    search_fields = ("user_id", "name", "phone_number")
    list_filter = ("name",)
    fieldsets = (
        (None, {
            "fields": ("user_id", "name")
        }),
        ("Контактная информация", {
            "fields": ("phone_number", "delivery_address"),
        }),
    )
