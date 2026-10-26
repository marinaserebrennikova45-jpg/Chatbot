"""GIRLS | Stream Agency bilingual recruitment bot for Hilly."""
import logging
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters,
)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "")
CLAIM_CODE = os.getenv("MANAGER_CLAIM_CODE", "")
MANAGER = os.getenv("MANAGER_USERNAME", "girls_mngr").lstrip("@").lower()
DB = Path(os.getenv("DB_PATH", "agency_bot.sqlite3"))
LANG, CONSENT, NAME, AGE, COUNTRY, EXPERIENCE, HOURS, LANGUAGES, USERNAME, WHEN, PHOTOS = range(11)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

TEXT = {
 "ru": {
  "welcome": "💗 GIRLS | Stream Agency\nВыбери язык / Choose your language:",
  "menu": "💗 Главное меню GIRLS | Stream Agency",
  "apply": "📝 Заполнить анкету", "how": "✨ Как это работает",
  "terms": "💰 Условия и выплаты", "contact": "💬 Написать менеджеру",
  "consent": "Для рассмотрения заявки мы передадим менеджеру @girls_mngr твои ответы и 2–3 обычные фотографии. Не присылай интимные фото или документы. Только 18+. Можно отменить анкету командой /cancel. Согласна на передачу данных?",
  "yes": "Согласна", "no": "Отказаться",
  "questions": ["Как тебя зовут?", "Сколько тебе полных лет? (18+)", "В какой стране ты живёшь?", "Есть ли опыт стриминга?", "Сколько часов в день готова уделять эфирам?", "На каких языках говоришь?", "Твой Telegram username (или напиши «нет»)?", "Когда хочешь начать?"],
  "photo": "📷 Пришли 2–3 свои обычные фотографии, по одной. После второй появится кнопка «Готово».",
  "done": "✅ Готово", "more": "Фото получено: {count}/3.",
  "few": "Нужно минимум 2 фотографии.", "many": "Получено 3 фото. Нажми «Готово».",
  "age": "Укажи возраст числом, от 18 лет.", "minor": "Заявки принимаются только от совершеннолетних (18+).",
  "cancel": "Анкета отменена, данные текущей заявки очищены.",
  "sent": "💗 Спасибо! Анкета и фотографии отправлены менеджеру.",
  "no_manager": "Менеджер пока не подключён. Попробуй позже.",
  "failed": "Не удалось передать заявку. Попробуй снова позже.",
  "how_text": "Изучи условия, заполни анкету, затем менеджер расскажет о дальнейших шагах.",
  "terms_text": "Доход зависит от активности и действующих правил Hilly. Гарантированного дохода нет. Уточни актуальные условия у менеджера.",
  "deleted": "Текущая анкета очищена. Для удаления уже отправленных менеджеру сообщений напиши @girls_mngr.",
  "text": "Пожалуйста, ответь текстовым сообщением.",
 },
 "en": {
  "welcome": "💗 GIRLS | Stream Agency\nChoose your language / Выбери язык:",
  "menu": "💗 GIRLS | Stream Agency main menu",
  "apply": "📝 Apply to join", "how": "✨ How it works",
  "terms": "💰 Terms & payments", "contact": "💬 Contact manager",
  "consent": "To review your application we will send your answers and 2–3 ordinary photos to manager @girls_mngr. Do not send intimate pictures or ID documents. Adults 18+ only. You may cancel with /cancel. Do you consent to this data transfer?",
  "yes": "I agree", "no": "Decline",
  "questions": ["What's your name?", "How old are you? (18+)", "Which country do you live in?", "Have you streamed before?", "How many hours per day can you stream?", "What languages do you speak?", "Your Telegram username (or type none)?", "When would you like to start?"],
  "photo": "📷 Send 2–3 ordinary photos of yourself, one at a time. A Done button appears after the second photo.",
  "done": "✅ Done", "more": "Photo received: {count}/3.",
  "few": "Please send at least 2 photos.", "many": "Received 3 photos. Tap Done.",
  "age": "Enter a numeric age of 18 or older.", "minor": "Only applicants aged 18+ may apply.",
  "cancel": "Application cancelled and current data cleared.",
  "sent": "💗 Thank you! Your application and photos were sent to the manager.",
  "no_manager": "The manager is not connected yet. Please try later.",
  "failed": "Could not send the application. Please try again later.",
  "how_text": "Review the terms, apply, and the manager will explain the next steps.",
  "terms_text": "Income varies with activity and current Hilly rules. No earnings are guaranteed. Ask the manager about current terms.",
  "deleted": "Your current application is cleared. To request deletion of messages already sent to the manager, contact @girls_mngr.",
  "text": "Please reply with text.",
 }
}
KEYS = ["name", "age", "country", "experience", "hours", "languages", "username", "when"]
STATES = [NAME, AGE, COUNTRY, EXPERIENCE, HOURS, LANGUAGES, USERNAME, WHEN]

def t(ctx, key):
    return TEXT[ctx.user_data.get("lang", "en")][key]

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")

def manager_id():
    with sqlite3.connect(DB) as db:
        row = db.execute("SELECT value FROM settings WHERE key='manager_chat_id'").fetchone()
        return int(row[0]) if row else None

def menu(ctx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(ctx, "apply"), callback_data="apply")],
        [InlineKeyboardButton(t(ctx, "how"), callback_data="how"), InlineKeyboardButton(t(ctx, "terms"), callback_data="terms")],
        [InlineKeyboardButton(t(ctx, "contact"), url="https://t.me/girls_mngr")],
        [InlineKeyboardButton("🇷🇺 / 🇬🇧", callback_data="language")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.effective_message.reply_text(
        "💗 GIRLS | Stream Agency\nChoose language / Выбери язык:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
             InlineKeyboardButton("🇬🇧 English", callback_data="lang:en")]
        ])
    )
    return LANG

async def choose_language(update, ctx):
    q = update.callback_query
    await q.answer()
    ctx.user_data["lang"] = q.data.split(":")[1]
    await q.message.reply_text(t(ctx, "menu"), reply_markup=menu(ctx))
    return ConversationHandler.END

async def menu_command(update, ctx):
    await update.effective_message.reply_text(t(ctx, "menu"), reply_markup=menu(ctx))

async def actions(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == "language":
        return await start(update, ctx)
    if q.data == "how":
        await q.message.reply_text(t(ctx, "how_text"), reply_markup=menu(ctx))
    elif q.data == "terms":
        await q.message.reply_text(t(ctx, "terms_text"), reply_markup=menu(ctx))
    elif q.data == "apply":
        ctx.user_data.pop("answers", None)
        ctx.user_data.pop("photos", None)
        await q.message.reply_text(t(ctx, "consent"), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(t(ctx, "yes"), callback_data="consent:yes"),
             InlineKeyboardButton(t(ctx, "no"), callback_data="consent:no")]
        ]))
        return CONSENT
    return ConversationHandler.END

async def consent(update, ctx):
    q = update.callback_query
    await q.answer()
    if q.data == "consent:no":
        await q.message.reply_text(t(ctx, "cancel"))
        return ConversationHandler.END
    ctx.user_data["answers"] = {}
    ctx.user_data["photos"] = []
    await q.message.reply_text(t(ctx, "questions")[0])
    return NAME

async def answer(update, ctx):
    state = next((i for i, s in enumerate(STATES) if s == ctx.user_data.get("_state")), None)
    # The current question is tracked explicitly by per-state handlers below.
    return ConversationHandler.END

def make_answer(index):
    async def handle(update, ctx):
        value = (update.effective_message.text or "").strip()
        if not value or len(value) > 500:
            await update.message.reply_text(t(ctx, "text"))
            return STATES[index]
        if index == 1:
            try:
                age = int(value)
            except ValueError:
                await update.message.reply_text(t(ctx, "age"))
                return AGE
            if age < 18:
                ctx.user_data.pop("answers", None)
                ctx.user_data.pop("photos", None)
                await update.message.reply_text(t(ctx, "minor"))
                return ConversationHandler.END
            if age > 120:
                await update.message.reply_text(t(ctx, "age"))
                return AGE
        ctx.user_data.setdefault("answers", {})[KEYS[index]] = value
        if index < 7:
            await update.message.reply_text(t(ctx, "questions")[index + 1])
            return STATES[index + 1]
        await update.message.reply_text(t(ctx, "photo"))
        return PHOTOS
    return handle

async def photo_received(update, ctx):
    photos = ctx.user_data.setdefault("photos", [])
    if len(photos) >= 3:
        await update.message.reply_text(t(ctx, "many"))
        return PHOTOS
    photos.append(update.message.photo[-1].file_id)
    count = len(photos)
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(t(ctx, "done"), callback_data="photos:done")]]) if count >= 2 else None
    await update.message.reply_text(t(ctx, "more").format(count=count), reply_markup=keyboard)
    return PHOTOS

async def photo_done(update, ctx):
    q = update.callback_query
    await q.answer()
    photos = ctx.user_data.get("photos", [])
    if len(photos) < 2:
        await q.message.reply_text(t(ctx, "few"))
        return PHOTOS
    mid = manager_id()
    if not mid:
        await q.message.reply_text(t(ctx, "no_manager"))
        return PHOTOS
    a = ctx.user_data.get("answers", {})
    fields = "\n".join(f"{k}: {a.get(k, '-')}" for k in KEYS)
    sender = update.effective_user
    report = f"💗 GIRLS | Stream Agency — NEW APPLICATION\n{fields}\nTelegram sender ID: {sender.id}\nTelegram: @{sender.username or 'none'}"
    try:
        await ctx.bot.send_message(chat_id=mid, text=report)
        for file_id in photos:
            await ctx.bot.send_photo(chat_id=mid, photo=file_id)
    except Exception:
        log.exception("Failed to forward application")
        await q.message.reply_text(t(ctx, "failed"))
        return PHOTOS
    ctx.user_data.pop("answers", None)
    ctx.user_data.pop("photos", None)
    await q.message.reply_text(t(ctx, "sent"), reply_markup=menu(ctx))
    return ConversationHandler.END

async def cancel(update, ctx):
    lang = ctx.user_data.get("lang", "en")
    ctx.user_data.clear()
    ctx.user_data["lang"] = lang
    await update.effective_message.reply_text(t(ctx, "cancel"))
    return ConversationHandler.END

async def delete_me(update, ctx):
    ctx.user_data.pop("answers", None)
    ctx.user_data.pop("photos", None)
    await update.effective_message.reply_text(t(ctx, "deleted"))
    return ConversationHandler.END

async def claim(update, ctx):
    if update.effective_chat.type != "private":
        return
    if not CLAIM_CODE or len(CLAIM_CODE) < 24 or CLAIM_CODE == "REPLACE_WITH_LONG_RANDOM_SECRET":
        await update.message.reply_text("Manager claim is not configured.")
        return
    if update.effective_user.username is None or update.effective_user.username.lower() != MANAGER:
        await update.message.reply_text("This command is restricted to the configured manager.")
        return
    args = ctx.args or []
    if len(args) != 1 or args[0] != CLAIM_CODE:
        await update.message.reply_text("Invalid claim code.")
        return
    with sqlite3.connect(DB) as db:
        db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES ('manager_chat_id',?)", (str(update.effective_chat.id),))
    await update.message.reply_text("💗 Manager connected. Delete your claim command message.")

async def fallback_text(update, ctx):
    await update.message.reply_text(t(ctx, "text"))
    return PHOTOS

def main():
    if not TOKEN or TOKEN == "PASTE_BOTFATHER_TOKEN_HERE":
        raise RuntimeError("Set BOT_TOKEN in environment or .env")
    init_db()
    app = Application.builder().token(TOKEN).build()
    states = {
        LANG: [CallbackQueryHandler(choose_language, pattern=r"^lang:(ru|en)$")],
        CONSENT: [CallbackQueryHandler(consent, pattern=r"^consent:(yes|no)$")],
        PHOTOS: [
            MessageHandler(filters.PHOTO & ~filters.COMMAND, photo_received),
            CallbackQueryHandler(photo_done, pattern=r"^photos:done$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_text)
        ],
    }
    for i, state in enumerate(STATES):
        states[state] = [MessageHandler(filters.TEXT & ~filters.COMMAND, make_answer(i))]
    flow = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(actions, pattern=r"^(apply|how|terms|language)$")],
        states=states,
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler("claim", claim), group=-1)
    app.add_handler(CommandHandler("delete_me", delete_me), group=-1)
    app.add_handler(CommandHandler("menu", menu_command), group=-1)
    app.add_handler(flow)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
