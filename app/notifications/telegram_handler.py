import structlog
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from app.repositories.feedback_repository import FeedbackRepository
from app.storage.database import SessionLocal

log = structlog.get_logger()


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    action_key = parts[0]
    result_id = int(parts[1])
    role_category = parts[2] if len(parts) > 2 else "other"

    action_map = {"approve": "approved", "save": "saved", "ignore": "ignored"}
    action = action_map.get(action_key, action_key)

    async with SessionLocal() as session:
        async with session.begin():
            repo = FeedbackRepository(session)
            await repo.save_feedback(result_id=result_id, action=action, role_category=role_category)

    label_map = {"approved": "✅ CV inviato", "saved": "⭐ Salvato", "ignored": "❌ Ignorato"}
    label = label_map.get(action, action)

    original = query.message.text if query.message else ""
    await query.edit_message_text(text=f"{original}\n\n{label}", reply_markup=None)
    log.info("telegram.feedback_saved", result_id=result_id, action=action)


async def _handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Profile management: visit /admin/profile")


async def _handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Stats: visit /admin/stats")


def build_application(bot_token: str) -> Application:  # type: ignore[type-arg]
    app = Application.builder().token(bot_token).build()
    app.add_handler(CallbackQueryHandler(_handle_callback))
    app.add_handler(CommandHandler("profile", _handle_profile))
    app.add_handler(CommandHandler("stats", _handle_stats))
    return app
