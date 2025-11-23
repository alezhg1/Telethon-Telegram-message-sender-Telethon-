import asyncio
import os
import re
from telethon import TelegramClient
from telethon.tl.types import InputMessagesFilterDocument
from telethon.errors import RPCError, FloodWaitError
import logging
from config import API_ID, API_HASH, PHONE_NUMBER, SESSION_FILE

logging.getLogger('telethon').setLevel(logging.WARNING)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)


class TelegramSender:
    def __init__(self, client):
        self.client = client

    async def safe_send_message(self, chat, message, max_retries=3):
        for attempt in range(max_retries):
            try:
                if not self.client.is_connected():
                    print("🔌 Соединение разорвано, переподключаемся...")
                    await self.client.connect()

                await self.client.send_message(chat.entity, message)
                return True

            except FloodWaitError as e:
                wait_time = e.seconds
                print(f"⏳ Flood wait: ждем {wait_time} секунд...")
                await asyncio.sleep(wait_time + 1)
                continue

            except RPCError as e:
                print(f"❌ Ошибка RPC (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                    continue
                else:
                    return False

            except Exception as e:
                print(f"❌ Неожиданная ошибка (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)
                    continue
                else:
                    return False

        return False

    async def get_all_chats(self):
        try:
            dialogs = await self.client.get_dialogs()
            valid_dialogs = []
            for dialog in dialogs:
                if dialog and dialog.entity:
                    valid_dialogs.append(dialog)
            return valid_dialogs
        except Exception as e:
            print(f"❌ Ошибка получения чатов: {e}")
            return []

    def display_chats(self, dialogs):
        print("\n" + "=" * 60)
        print("📋 СПИСОК ВАШИХ ЧАТОВ:")
        print("=" * 60)
        for i, dialog in enumerate(dialogs, 1):
            chat_type = self.get_chat_type(dialog)
            chat_name = self.get_chat_display_name(dialog.entity)
            unread = f" ({dialog.unread_count} непрочитанных)" if dialog.unread_count else ""
            print(f"{i:3d}. {chat_type} {chat_name}{unread}")
        print("=" * 60)

    def get_chat_type(self, dialog):
        if not dialog or not dialog.entity:
            return "❓"
        if dialog.is_user:
            return "👤"
        elif dialog.is_channel:
            return "📢"
        elif dialog.is_group:
            return "👥"
        else:
            return "💬"

    def get_chat_display_name(self, chat):
        if not chat:
            return "Unknown Chat"
        if hasattr(chat, 'title') and chat.title:
            return chat.title
        elif hasattr(chat, 'first_name'):
            first_name = getattr(chat, 'first_name', '')
            last_name = getattr(chat, 'last_name', '')
            name = f"{first_name} {last_name}".strip()
            return name if name else f"User {chat.id}"
        return f"Chat {chat.id}"

    def select_chat(self, dialogs):
        while True:
            try:
                choice = input("\n🎯 Введите номер чата для отправки: ").strip()
                if not choice:
                    print("❌ Введите номер чата")
                    continue

                chat_number = int(choice)
                if 1 <= chat_number <= len(dialogs):
                    selected_chat = dialogs[chat_number - 1]
                    if not selected_chat or not selected_chat.entity:
                        print("❌ Выбран невалидный чат")
                        continue

                    chat_name = self.get_chat_display_name(selected_chat.entity)
                    print(f"✅ Выбран чат: {chat_name}")
                    return selected_chat
                else:
                    print(f"❌ Неверный номер. Доступно от 1 до {len(dialogs)}")

            except ValueError:
                print("❌ Введите корректный номер")
            except KeyboardInterrupt:
                print("\n👋 Программа завершена")
                exit()

    def get_file_path(self):
        while True:
            try:
                file_path = input("\n📁 Введите путь к файлу .txt: ").strip()
                if not file_path:
                    print("❌ Введите путь к файлу")
                    continue

                if not file_path.lower().endswith('.txt'):
                    file_path += '.txt'

                if not os.path.exists(file_path):
                    print(f"❌ Файл '{file_path}' не найден")
                    continue

                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    print("❌ Файл пустой")
                    continue

                print(f"✅ Файл найден: {file_path} ({file_size} байт)")
                return file_path

            except KeyboardInterrupt:
                print("\n👋 Программа завершена")
                exit()

    def read_messages_from_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                messages = [line.strip() for line in file if line.strip()]

            if not messages:
                print("❌ В файле нет сообщений (все строки пустые)")
                return None

            print(f"📨 Прочитано сообщений: {len(messages)}")
            print("\n📋 Первые 5 сообщений:")
            print("-" * 40)
            for i, msg in enumerate(messages[:5], 1):
                preview = msg[:50] + "..." if len(msg) > 50 else msg
                print(f"{i}. {preview}")
            if len(messages) > 5:
                print(f"... и еще {len(messages) - 5} сообщений")
            print("-" * 40)
            return messages

        except UnicodeDecodeError:
            print("❌ Ошибка: файл должен быть в кодировке UTF-8")
            return None
        except Exception as e:
            print(f"❌ Ошибка чтения файла: {e}")
            return None

    def confirm_sending(self, chat, message_count):
        if not chat or not chat.entity:
            print("❌ Ошибка: выбран невалидный чат")
            return False

        chat_name = self.get_chat_display_name(chat.entity)
        print("\n" + "=" * 60)
        print("🚀 ПОДТВЕРЖДЕНИЕ ОТПРАВКИ")
        print("=" * 60)
        print(f"💬 Чат: {chat_name}")
        print(f"📨 Сообщений: {message_count}")
        print("=" * 60)

        while True:
            try:
                choice = input("\nОтправить сообщения? (да/нет): ").strip().lower()
                if choice in ['да', 'д', 'yes', 'y', '1']:
                    return True
                elif choice in ['нет', 'н', 'no', 'n', '0']:
                    print("❌ Отправка отменена")
                    return False
                else:
                    print("❌ Введите 'да' или 'нет'")
            except KeyboardInterrupt:
                print("\n👋 Программа завершена")
                return False

    async def send_messages(self, chat, messages):
        if not chat or not chat.entity:
            print("❌ Ошибка: невалидный чат для отправки")
            return

        chat_name = self.get_chat_display_name(chat.entity)
        total_messages = len(messages)
        sent_count = 0
        failed_count = 0

        print(f"\n📤 Начинаем отправку в чат: {chat_name}")
        print("⏳ Это может занять некоторое время...")

        for i, message in enumerate(messages, 1):
            try:
                if not message or not message.strip():
                    print(f"⚠️ Пропущено пустое сообщение {i}")
                    continue

                success = await self.safe_send_message(chat, message)

                if success:
                    sent_count += 1
                    if i % 10 == 0 or i == total_messages:
                        print(f"📨 Отправлено {i}/{total_messages} сообщений")
                else:
                    failed_count += 1
                    print(f"❌ Не удалось отправить сообщение {i}")

                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"❌ Критическая ошибка отправки сообщения {i}: {e}")
                failed_count += 1
                continue

        print("\n" + "=" * 60)
        print("📊 ИТОГИ ОТПРАВКИ:")
        print("=" * 60)
        print(f"✅ Успешно отправлено: {sent_count}")
        print(f"❌ Не отправлено: {failed_count}")
        print(f"💬 Чат: {chat_name}")
        print("=" * 60)

    async def run(self):
        try:
            print("🤖 ЗАПУСК ТЕЛЕГРАМ ОТПРАВИТЕЛЯ")
            print("=" * 50)

            dialogs = await self.get_all_chats()

            if not dialogs:
                print("❌ Чаты не найдены или произошла ошибка при загрузке")
                return

            print(f"✅ Загружено чатов: {len(dialogs)}")
            self.display_chats(dialogs)

            selected_chat = self.select_chat(dialogs)
            if not selected_chat:
                print("❌ Не удалось выбрать чат")
                return

            file_path = self.get_file_path()
            messages = self.read_messages_from_file(file_path)

            if not messages:
                return

            if not self.confirm_sending(selected_chat, len(messages)):
                return

            await self.send_messages(selected_chat, messages)
            print("\n🎉 Работа завершена!")

        except Exception as e:
            print(f"💥 Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()

        except KeyboardInterrupt:
            print("\n👋 Программа завершена пользователем")


async def main():
    try:
        print("🔌 Подключаемся к Telegram...")
        await client.start(phone=PHONE_NUMBER)
        print("✅ Клиент запущен успешно!")

        sender = TelegramSender(client)
        await sender.run()

    except Exception as e:
        print(f"💥 Ошибка подключения: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if client.is_connected():
            await client.disconnect()
        print("🔌 Соединение закрыто")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена")
