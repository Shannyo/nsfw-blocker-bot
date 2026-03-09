import asyncio
import io
import logging
import sys
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from ultralytics import YOLO
from PIL import Image


TOKEN = 'YOUR_TOKEN'
MODEL_PATH = 'NSFWai.pt'
CONFIDENCE_THRESHOLD = 0.60
LOG_FILE = "detect_logs.txt"
FORBIDDEN_LABELS = ['nsfw']
MSK = timezone(timedelta(hours=3))
logging.basicConfig(level=logging.INFO, format='%(message)s')

def get_msk_time():
    return datetime.now(MSK)
def log_to_file(username, class_name, confidence):
    now = get_msk_time()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp} MSK] User: @{username} | Result: {class_name} | Conf: {confidence:.2%}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)
        f.flush()
try:
    model = YOLO(MODEL_PATH)
    print(f"Model loaded. Classes: {model.names}")
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)
dp = Dispatcher()

@dp.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    try:
        photo = message.photo[-1]
        file_io = await bot.download(photo)

        image = Image.open(file_io)
        results = model(image, verbose=False)
        result = results[0]

        top_idx = result.probs.top1
        class_name = result.names[top_idx].lower().strip()
        confidence = float(result.probs.top1conf.item())

        current_time = get_msk_time().strftime('%H:%M:%S')
        print(f"[{current_time} MSK] @{message.from_user.username}: {class_name} ({confidence:.2%})")

        if class_name in FORBIDDEN_LABELS and confidence >= CONFIDENCE_THRESHOLD:
            log_to_file(message.from_user.username, class_name, confidence)

            try:
                await message.delete()
                print(f"DELETED")
            except Exception as e:
                print(f"Delete failed: {e}")

            warn = await message.answer(
                f"**{message.from_user.first_name}**, NSFW detected. Removed.",
                parse_mode="Markdown"
            )
            await asyncio.sleep(5)
            await warn.delete()

    except Exception as e:
        print(f"Error in handle_photo: {e}")

async def main():
    bot = Bot(token=TOKEN)
    print("="*30)
    print("BOT STARTED")
    print(f"Logs: {LOG_FILE}")
    print("="*30)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")