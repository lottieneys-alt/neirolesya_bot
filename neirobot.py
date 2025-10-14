import asyncio
import logging
import json
import os
import time
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ADMIN_USER_ID = 352362080
BOT_TOKEN = os.getenv("8222079334:AAFVJ5TQAHL3VR4uNiy-M1mTvXEV_QDfL4U")

class NotificationBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.users_file = 'users.json'
        self.messages_file = 'messages.json'
        self.schedule_file = 'schedule.json'
        self.admin_id = ADMIN_USER_ID
        self.load_data()

    def load_data(self):
        def load_or_create(path, default):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except FileNotFoundError:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(default, f, indent=2, ensure_ascii=False)
                return default

        self.users = load_or_create(self.users_file, [])
        self.messages = load_or_create(self.messages_file, {})
        self.schedule_config = load_or_create(self.schedule_file, {})

    def save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)

    def save_messages(self):
        with open(self.messages_file, 'w', encoding='utf-8') as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)

    def save_schedule(self):
        with open(self.schedule_file, 'w', encoding='utf-8') as f:
            json.dump(self.schedule_config, f, indent=2, ensure_ascii=False)

    def is_admin(self, user_id):
        return user_id == self.admin_id

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in self.users:
            self.users.append(user_id)
            self.save_users()
            await update.message.reply_text("Добро пожаловать! Вы подписаны на рассылку.")
        else:
            await update.message.reply_text("Вы уже подписаны!")

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.users:
            self.users.remove(user_id)
            self.save_users()
            await update.message.reply_text("Вы отписались от рассылки.")
        else:
            await update.message.reply_text("Вы не подписаны.")

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return

        text = (
            "👑 Панель администратора\n\n"
            "📝 Добавить сообщение:\n"
            "/addmsg [ключ] [тип] [текст]\n"
            "Тип: text | photo | video\n"
            "Пример: /addmsg утро text Доброе утро!\n\n"
            "⏰ Расписание:\n"
            "/addtime [ключ] [ЧЧ:ММ]\n"
            "/deltime [ключ] [ЧЧ:ММ]\n"
            "/listtimes\n\n"
            "📋 Сообщения:\n"
            "/listmsg\n"
            "/delmsg [ключ]\n"
        )
        await update.message.reply_text(text)

    async def add_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return

        if len(context.args) < 3:
            await update.message.reply_text("❌ Использование: /addmsg [ключ] [тип] [текст]")
            return

        key = context.args[0]
        msg_type = context.args[1]
        text = ' '.join(context.args[2:])

        if msg_type not in ["text", "photo", "video"]:
            await update.message.reply_text("❌ Тип должен быть: text, photo или video")
            return

        # Если это фото или видео — ожидаем файл в ответном сообщении
        if msg_type in ["photo", "video"] and not update.message.reply_to_message:
            await update.message.reply_text("📎 Пришлите фото или видео и ответьте на него этой командой.")
            return

        file_id = None
        if msg_type == "photo" and update.message.reply_to_message.photo:
            file_id = update.message.reply_to_message.photo[-1].file_id
        elif msg_type == "video" and update.message.reply_to_message.video:
            file_id = update.message.reply_to_message.video.file_id
        elif msg_type != "text":
            await update.message.reply_text("❌ Файл не найден.")
            return

        self.messages[key] = {"type": msg_type, "content": text, "file_id": file_id}
        self.save_messages()
        await update.message.reply_text(f"✅ Сообщение '{key}' добавлено!")

    async def delete_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        if not context.args:
            await update.message.reply_text("❌ Использование: /delmsg [ключ]")
            return

        key = context.args[0]
        if key in self.messages:
            del self.messages[key]
            self.save_messages()
            if key in self.schedule_config:
                del self.schedule_config[key]
                self.save_schedule()
            await update.message.reply_text(f"✅ Сообщение '{key}' удалено.")
        else:
            await update.message.reply_text("❌ Сообщение не найдено.")

    async def list_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        if not self.messages:
            await update.message.reply_text("📭 Нет сообщений.")
            return
        text = "📋 Сообщения:\n\n"
        for key, msg in self.messages.items():
            text += f"{key} — {msg['type']}: {msg['content'][:50]}\n"
        await update.message.reply_text(text)

    async def add_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /addtime [ключ] [ЧЧ:ММ]")
            return

        key, time_str = context.args[0], context.args[1]
        if key not in self.messages:
            await update.message.reply_text(f"❌ Сообщение '{key}' не найдено.")
            return
        try:
            time.strptime(time_str, "%H:%M")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени (ЧЧ:ММ).")
            return

        self.schedule_config.setdefault(key, [])
        if time_str not in self.schedule_config[key]:
            self.schedule_config[key].append(time_str)
            self.save_schedule()
            await update.message.reply_text(f"✅ Время {time_str} добавлено для '{key}'")
        else:
            await update.message.reply_text("❌ Уже добавлено.")

    async def delete_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /deltime [ключ] [ЧЧ:ММ]")
            return

        key, time_str = context.args[0], context.args[1]
        if key not in self.schedule_config or time_str not in self.schedule_config[key]:
            await update.message.reply_text("❌ Не найдено.")
            return
        self.schedule_config[key].remove(time_str)
        if not self.schedule_config[key]:
            del self.schedule_config[key]
        self.save_schedule()
        await update.message.reply_text(f"✅ Удалено {time_str} для '{key}'")

    async def list_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        if not self.schedule_config:
            await update.message.reply_text("⏰ Нет расписаний.")
            return
        text = "⏰ Расписания:\n\n"
        for key, times in self.schedule_config.items():
            text += f"{key}: {', '.join(times)}\n"
        await update.message.reply_text(text)

    async def send_scheduled_message(self, message_key):
        msg = self.messages.get(message_key)
        if not msg:
            return

        for user_id in self.users:
            try:
                if msg["type"] == "text":
                    await self.application.bot.send_message(chat_id=user_id, text=msg["content"])
                elif msg["type"] == "photo":
                    await self.application.bot.send_photo(chat_id=user_id, photo=msg["file_id"], caption=msg["content"])
                elif msg["type"] == "video":
                    await self.application.bot.send_video(chat_id=user_id, video=msg["file_id"], caption=msg["content"])
            except Exception as e:
                logging.error(f"Ошибка отправки пользователю {user_id}: {e}")

    async def scheduler_loop(self):
        while True:
            now = datetime.now().strftime("%H:%M")
            for key, times in self.schedule_config.items():
                if now in times:
                    asyncio.create_task(self.send_scheduled_message(key))
            await asyncio.sleep(60)

    def run(self):
        app = self.application
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("stop", self.stop))
        app.add_handler(CommandHandler("admin", self.admin_panel))
        app.add_handler(CommandHandler("addmsg", self.add_message))
        app.add_handler(CommandHandler("delmsg", self.delete_message))
        app.add_handler(CommandHandler("listmsg", self.list_messages))
        app.add_handler(CommandHandler("addtime", self.add_schedule))
        app.add_handler(CommandHandler("deltime", self.delete_schedule))
        app.add_handler(CommandHandler("listtimes", self.list_schedule))
        asyncio.create_task(self.scheduler_loop())
        logging.info("Бот запущен!")
        app.run_polling()

if __name__ == "__main__":
    bot = NotificationBot(BOT_TOKEN)
    bot.run()
