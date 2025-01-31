import os
import django
import sys
import pytz
from telegram import Bot, ReplyKeyboardMarkup, KeyboardButton, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from asgiref.sync import sync_to_async
from django.db.models import Prefetch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DivaKids.settings')
django.setup()

from shop.models import Order, OrderItem, UserProfile

TOKEN = '7534268318:AAERP3Kbu5NS4K0MnoiFRzLcsDyIRzGYOJk'


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    keyboard = [
        [KeyboardButton(text="🛒 Заказать", web_app=WebAppInfo(
            url=f"https://divakids.pythonanywhere.com/shop/products/?user_id={user_id}"))],
        [KeyboardButton(text="📦 Мои заказы")],
        [KeyboardButton(text="📝 Мои данные")],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    greeting_message = (
        f"👋 Добро пожаловать, {user_name}, в DivaKids! 💖\n\n"
        "Мы рады видеть вас! У нас вы найдете стильную и качественную одежду для детей. 👕👗👶\n\n"
        "Выберите действие:"
    )
    await update.message.reply_text(greeting_message, reply_markup=markup)


@sync_to_async
def get_user_orders(user_id):
    return list(Order.objects.filter(user_id=user_id).prefetch_related('orderitem_set__product'))


async def get_user_orders_async(user_id):
    """Асинхронно получает заказы пользователя."""
    return await sync_to_async(list)(
        Order.objects.prefetch_related(
            Prefetch('orderitem_set', queryset=OrderItem.objects.select_related('product', 'size'))
        ).filter(user_id=user_id)
    )


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    orders = await get_user_orders_async(user_id)

    if not orders:
        await update.message.reply_text("📭 <b>У вас пока нет заказов.</b>", parse_mode="HTML")
        return

    tz = pytz.timezone("Asia/Tashkent")
    message = "<b>📦 Ваши заказы:</b>\n\n"

    for order in orders:
        order_time = order.created_at.astimezone(tz).strftime("%d-%m-%Y %H:%M")
        message += (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 <b>Заказ №{order.id}</b>\n"
            f"📅 <i>Дата заказа:</i> {order_time}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>📋 Товары в заказе:</b>\n"
        )

        for item in order.orderitem_set.all():
            size_text = f"📏 Размер: <code>{item.size.size}</code>" if item.size else "📏 Размер: <i>Не указан</i>"
            price_total = item.product.price * item.quantity
            message += (
                f"🔹 <b>{item.product.name}</b>\n"
                f"   {size_text}\n"
                f"   🛍 Количество: <b>{item.quantity}</b>\n"
                f"   💰 Цена: <b>{price_total:,} UZS</b>\n\n"
            )

        message += f"💳 <b>Общая стоимость:</b> <code>{order.total_price:,} UZS</code>\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    await update.message.reply_text(message, parse_mode="HTML")


async def my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    profile, created = await sync_to_async(UserProfile.objects.get_or_create)(user_id=user_id)

    if created or not profile.name:
        await update.message.reply_text("📝 У вас пока нет сохраненных данных. Пожалуйста, введите ваше имя:")
        context.user_data['awaiting_name'] = True
    else:
        await update.message.reply_text(
            f"📝 Ваши данные:\n\n"
            f"👤 Имя: {profile.name}\n"
            f"📞 Номер телефона: {profile.phone_number}\n"
            f"🏠 Адрес доставки: {profile.delivery_address}\n\n"
            "Чтобы изменить данные, введите /edit_data"
        )


async def edit_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    context.user_data['awaiting_name'] = True
    await update.message.reply_text("📝 Введите ваше имя:")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if context.user_data.get('awaiting_name'):
        profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
        profile.name = text
        await sync_to_async(profile.save)()
        context.user_data['awaiting_name'] = False
        context.user_data['awaiting_phone'] = True

        keyboard = [
            [KeyboardButton(text="📞 Отправить мой контакт", request_contact=True)],
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📞 Теперь отправьте ваш номер телефона, нажав кнопку ниже:",
            reply_markup=markup,
        )

    elif context.user_data.get('awaiting_address'):
        profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
        profile.delivery_address = text
        await sync_to_async(profile.save)()
        context.user_data['awaiting_address'] = False

        keyboard = [
            [KeyboardButton(text="🛒 Заказать", web_app=WebAppInfo(
                url=f"https://divakids.pythonanywhere.com/production/products/?user_id={user_id}"))],
            [KeyboardButton(text="📦 Мои заказы")],
            [KeyboardButton(text="📝 Мои данные")],
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "✅ Ваши данные успешно сохранены!",
            reply_markup=markup,
        )

    else:
        # Обработка неизвестных команд
        await update.message.reply_text(
            "❌ Я не понимаю такую команду. Пожалуйста, воспользуйтесь кнопками ниже.",
            reply_markup=ReplyKeyboardMarkup(
                [
                    [KeyboardButton(text="🛒 Заказать", web_app=WebAppInfo(
                        url=f"https://divakids.pythonanywhere.com/production/products/?user_id={user_id}"))],
                    [KeyboardButton(text="📦 Мои заказы")],
                    [KeyboardButton(text="📝 Мои данные")],
                ],
                resize_keyboard=True,
            ),
        )


async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    contact = update.message.contact

    if context.user_data.get('awaiting_phone'):
        profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
        profile.phone_number = contact.phone_number
        await sync_to_async(profile.save)()
        context.user_data['awaiting_phone'] = False
        context.user_data['awaiting_address'] = True

        keyboard = [
            [KeyboardButton(text="📍 Отправить мою геолокацию", request_location=True)],
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🏠 Теперь отправьте ваш адрес, нажав кнопку ниже для отправки геолокации или введите адрес вручную:",
            reply_markup=markup,
        )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    location = update.message.location

    if context.user_data.get('awaiting_address'):
        profile = await sync_to_async(UserProfile.objects.get)(user_id=user_id)
        profile.delivery_address = f"{location.latitude}, {location.longitude}"
        await sync_to_async(profile.save)()
        context.user_data['awaiting_address'] = False

        keyboard = [
            [KeyboardButton(text="🛒 Заказать", web_app=WebAppInfo(
                url=f"https://divakids.pythonanywhere.com/production/products/?user_id={user_id}"))],
            [KeyboardButton(text="📦 Мои заказы")],
            [KeyboardButton(text="📝 Мои данные")],
        ]
        markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "✅ Ваши данные успешно сохранены!",
            reply_markup=markup,
        )


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Text("📦 Мои заказы"), my_orders))
    application.add_handler(MessageHandler(filters.Text("📝 Мои данные"), my_data))
    application.add_handler(CommandHandler("edit_data", edit_data))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.run_polling()


if __name__ == "__main__":
    main()
