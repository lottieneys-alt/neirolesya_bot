import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import json
import schedule
import time
import threading

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ADMIN_USER_ID = 352362080
BOT_TOKEN = "8222079334:AAFVJ5TQAHL3VR4uNiy-M1mTvXEV_QDfL4U"

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
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except FileNotFoundError:
            self.users = []
            
        try:
            with open(self.messages_file, 'r') as f:
                self.messages = json.load(f)
        except FileNotFoundError:
            self.messages = {}
            self.save_messages()
            
        try:
            with open(self.schedule_file, 'r') as f:
                self.schedule_config = json.load(f)
        except FileNotFoundError:
            self.schedule_config = {}
            self.save_schedule()
    
    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def save_messages(self):
        with open(self.messages_file, 'w') as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)
    
    def save_schedule(self):
        with open(self.schedule_file, 'w') as f:
            json.dump(self.schedule_config, f, indent=2)
    
    def is_admin(self, user_id):
        return user_id == self.admin_id
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in self.users:
            self.users.append(user_id)
            self.save_users()
            welcome_msg = self.messages.get("welcome", "Добро пожаловать! Вы подписались на рассылку.")
            await update.message.reply_text(welcome_msg)
            
            if self.is_admin(user_id):
                await update.message.reply_text("👑 Вы администратор! Используйте /admin для управления.")
        else:
            await update.message.reply_text("Вы уже подписаны на рассылку!")
    
    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in self.users:
            self.users.remove(user_id)
            self.save_users()
            await update.message.reply_text("Вы отписались от рассылки.")
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        admin_commands = """
👑 Панель администратора

📝 Управление сообщениями:
/addmsg [ключ] [текст] - Добавить сообщение
/editmsg [ключ] [текст] - Изменить сообщение  
/delmsg [ключ] - Удалить сообщение
/listmsg - Все сообщения
/testmsg [ключ] - Тест сообщения

⏰ Управление расписанием:
/addtime [ключ] [время] - Добавить время отправки
/deltime [ключ] [время] - Удалить время
/listtimes - Все расписания

📊 Другое:
/stats - Статистика
        """
        await update.message.reply_text(admin_commands)
    
    async def add_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /addmsg [ключ] [текст]")
            return
        
        key = context.args[0]
        text = ' '.join(context.args[1:])
        
        self.messages[key] = text
        self.save_messages()
        
        await update.message.reply_text(f"✅ Сообщение '{key}' добавлено!")
    
    async def edit_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /editmsg [ключ] [новый текст]")
            return
        
        key = context.args[0]
        new_text = ' '.join(context.args[1:])
        
        if key not in self.messages:
            await update.message.reply_text(f"❌ Сообщение '{key}' не найдено.")
            return
        
        self.messages[key] = new_text
        self.save_messages()
        await update.message.reply_text(f"✅ Сообщение '{key}' обновлено!")
    
    async def delete_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /delmsg [ключ]")
            return
        
        key = context.args[0]
        
        if key not in self.messages:
            await update.message.reply_text(f"❌ Сообщение '{key}' не найдено.")
            return
        
        del self.messages[key]
        self.save_messages()
        
        if key in self.schedule_config:
            del self.schedule_config[key]
            self.save_schedule()
        
        await update.message.reply_text(f"✅ Сообщение '{key}' удалено!")
    
    async def list_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if not self.messages:
            await update.message.reply_text("📭 Нет сообщений.")
            return
        
        message_list = "📋 Сообщения:\n\n"
        for key, text in self.messages.items():
            times = self.schedule_config.get(key, [])
            time_str = ", ".join(times) if times else "нет расписания"
            message_list += f"**{key}**: {text}\n⏰ Время: {time_str}\n\n"
        
        await update.message.reply_text(message_list)
    
    async def add_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /addtime [ключ] [время]")
            return
        
        key = context.args[0]
        time_str = context.args[1]
        
        if key not in self.messages:
            await update.message.reply_text(f"❌ Сначала создайте сообщение с ключом '{key}'")
            return
        
        try:
            time.strptime(time_str, '%H:%M')
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 09:00)")
            return
        
        if key not in self.schedule_config:
            self.schedule_config[key] = []
        
        if time_str in self.schedule_config[key]:
            await update.message.reply_text(f"❌ Время {time_str} уже добавлено для '{key}'")
            return
        
        self.schedule_config[key].append(time_str)
        self.save_schedule()
        
        await update.message.reply_text(f"✅ Время {time_str} добавлено для '{key}'")
        self.setup_schedule()
    
    async def delete_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /deltime [ключ] [время]")
            return
        
        key = context.args[0]
        time_str = context.args[1]
        
        if key not in self.schedule_config or time_str not in self.schedule_config[key]:
            await update.message.reply_text(f"❌ Время {time_str} не найдено для '{key}'")
            return
        
        self.schedule_config[key].remove(time_str)
        if not self.schedule_config[key]:
            del self.schedule_config[key]
        
        self.save_schedule()
        await update.message.reply_text(f"✅ Время {time_str} удалено для '{key}'")
        self.setup_schedule()
    
    async def list_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if not self.schedule_config:
            await update.message.reply_text("⏰ Нет настроенного расписания.")
            return
        
        schedule_list = "⏰ Расписание:\n\n"
        for key, times in self.schedule_config.items():
            schedule_list += f"**{key}**: {', '.join(times)}\n"
        
        await update.message.reply_text(schedule_list)
    
    async def test_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ Использование: /testmsg [ключ]")
            return
        
        key = context.args[0]
        
        if key not in self.messages:
            await update.message.reply_text(f"❌ Сообщение '{key}' не найдено.")
            return
        
        await update.message.reply_text(f"🧪 Тест '{key}':\n\n{self.messages[key]}")
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Нет доступа.")
            return
        
        stats_text = (
            f"📊 Статистика:\n"
            f"• Подписчиков: {len(self.users)}\n"
            f"• Сообщений: {len(self.messages)}\n"
            f"• Расписаний: {len(self.schedule_config)}"
        )
        await update.message.reply_text(stats_text)
    
    async def send_scheduled_message(self, message_key):
        if message_key in self.messages:
            for user_id in self.users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user_id, 
                        text=self.messages[message_key]
                    )
                except Exception as e:
                    logging.error(f"Ошибка отправки {user_id}: {e}")
    
    def setup_schedule(self):
        schedule.clear()
        for message_key, times in self.schedule_config.items():
            for time_str in times:
                schedule.every().day.at(time_str).do(
                    lambda msg=message_key: asyncio.run(self.send_scheduled_message(msg))
                )
    
    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def run(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stop", self.stop))
        self.application.add_handler(CommandHandler("admin", self.admin_panel))
        self.application.add_handler(CommandHandler("addmsg", self.add_message))
        self.application.add_handler(CommandHandler("editmsg", self.edit_message))
        self.application.add_handler(CommandHandler("delmsg", self.delete_message))
        self.application.add_handler(CommandHandler("listmsg", self.list_messages))
        self.application.add_handler(CommandHandler("addtime", self.add_schedule))
        self.application.add_handler(CommandHandler("deltime", self.delete_schedule))
        self.application.add_handler(CommandHandler("listtimes", self.list_schedule))
        self.application.add_handler(CommandHandler("testmsg", self.test_message))
        self.application.add_handler(CommandHandler("stats", self.stats))
        
        self.setup_schedule()
        
        scheduler_thread = threading.Thread(target=self.run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logging.info("Бот запущен!")
        self.application.run_polling()

if __name__ == "__main__":
    bot = NotificationBot(BOT_TOKEN)
    bot.run()
