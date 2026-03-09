import flet as ft
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F, types
from ultralytics import YOLO
from PIL import Image

BG_COLOR = "#0F0F0F"
CARD_BG = "#161616"
ACCENT = "#D32F2F" 
TEXT_SEC = "#9E9E9E"
LOG_FILE = "detect_logs.txt"
CONFIG_FILE = "config.txt"
MSK = timezone(timedelta(hours=3))

class NSFWLauncher:
    def __init__(self):
        self.is_running = False
        self.bot_task = None
        self.last_read_line = 0 
        
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write(f"--- New Logs: {datetime.now(MSK).strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        except:
            pass

    def get_msk_time(self):
        return datetime.now(MSK)

    def save_config(self, token):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(token.strip())
        self.add_local_log("Config saved")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except: pass
        return ""

    def log_to_file(self, username, class_name, confidence):
        now = self.get_msk_time()
        timestamp = now.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] @{username} | {class_name} ({confidence:.1%})\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def add_local_log(self, text):
        self.log_view.controls.append(ft.Text(text, color="blue", size=10))
        self.page.update()

    async def start_bot_engine(self, token, model_path):
        try:
            model = YOLO(f"models/{model_path}")
            bot = Bot(token=token)
            dp = Dispatcher()

            @dp.message(F.photo)
            async def handle_photo(message: types.Message):
                try:
                    photo = message.photo[-1]
                    file_io = await bot.download(photo)
                    image = Image.open(file_io)
                    results = model(image, verbose=False)
                    result = results[0]

                    top_idx = result.probs.top1
                    class_name = result.names[top_idx].lower().strip()
                    confidence = float(result.probs.top1conf.item())
                    
                    self.log_to_file(message.from_user.username or "User", class_name, confidence)

                    if class_name == 'nsfw' and confidence >= 0.60:
                        try:
                            await message.delete()
                            warn = await message.answer(f"NSFW content removed")
                            await asyncio.sleep(4)
                            await warn.delete()
                        except: pass
                except Exception as e:
                    with open(LOG_FILE, "a", encoding="utf-8") as f: 
                        f.write(f"Error: {e}\n")

            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
        except Exception as e:
            self.is_running = False
            self.add_local_log(f"Error: {e}")
            if self.page: self.page.update()

    async def monitor_logs(self):
        while True:
            if os.path.exists(LOG_FILE):
                try:
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if len(lines) > self.last_read_line:
                            new_lines = lines[self.last_read_line:]
                            for line in new_lines:
                                color = ACCENT if "nsfw" in line.lower() else "green"
                                if "New Logs" in line: color = TEXT_SEC
                                self.log_view.controls.append(ft.Text(line.strip(), color=color, size=10))
                            self.last_read_line = len(lines)
                            self.page.update()
                except: pass
            await asyncio.sleep(0.5)

    async def build(self, page: ft.Page):
        self.page = page
        page.title = "NSFW Blocker"
        page.bgcolor = BG_COLOR
        page.window.width, page.window.height = 900, 500
        page.window.resizable = False
        
        # Надежная настройка путей для иконки
        base_path = os.getcwd()
        page.assets_dir = os.path.join(base_path, "assets")
        icon_path = os.path.join(base_path, "assets", "logo.png")
        
        if os.path.exists(icon_path):
            page.window.icon = icon_path

        CENTER = ft.Alignment(0, 0)

        logo_img = ft.Image(
            src="logo.png", 
            width=36, 
            height=36, 
            fit="contain"
        )

        saved_token = self.load_config()
        self.token_input = ft.TextField(
            label="Bot Token", value=saved_token, password=True, 
            can_reveal_password=True, border_color="#333333", text_size=12
        )
        
        if not os.path.exists("models"): os.makedirs("models")
        models = [f for f in os.listdir("models") if f.endswith(".pt")]
        self.model_dropdown = ft.Dropdown(
            label="Model", options=[ft.dropdown.Option(m) for m in models], 
            value=models[0] if models else None, text_size=12
        )
        
        self.log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)

        async def toggle_bot(e):
            if not self.is_running:
                if not self.token_input.value: return
                self.is_running = True
                self.btn_text.value = "Stop"
                self.start_btn.bgcolor = "#212121"
                self.bot_task = asyncio.create_task(self.start_bot_engine(self.token_input.value, self.model_dropdown.value))
            else:
                self.is_running = False
                if self.bot_task: self.bot_task.cancel()
                self.btn_text.value = "Start"
                self.start_btn.bgcolor = ACCENT
            page.update()

        self.save_btn = ft.Container(
            content=ft.Text("Save Config", size=10, weight="bold"),
            bgcolor="#333333",
            padding=ft.padding.symmetric(horizontal=30, vertical=15),
            border_radius=10,
            on_click=lambda _: self.save_config(self.token_input.value),
            alignment=CENTER
        )

        self.btn_text = ft.Text("Start", weight="bold", size=11)
        self.start_btn = ft.Container(
            content=self.btn_text, 
            bgcolor=ACCENT, 
            padding=15, 
            border_radius=10, 
            on_click=toggle_bot, 
            alignment=CENTER,
            width=160
        )

        page.add(ft.Row([
            ft.Container(expand=1, padding=30, content=ft.Column([
                ft.Row([
                    logo_img,
                    ft.Text("NSFW-blocker-bot", size=24, weight="bold")
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=10, color="transparent"),
                self.token_input,
                ft.Container(height=15),
                self.model_dropdown,
                ft.Container(expand=True),
                ft.Row([self.save_btn, self.start_btn], spacing=10, alignment="start")
            ])),
            ft.Container(expand=1, padding=20, bgcolor=CARD_BG, border_radius=ft.BorderRadius(30, 0, 0, 30), content=ft.Column([
                ft.Text("Logs", weight="bold", size=11),
                ft.Container(content=self.log_view, expand=True, bgcolor=BG_COLOR, border_radius=15, padding=10, border=ft.Border.all(1, "#222222")),
                ft.Text(f"File Logs: {LOG_FILE}", size=9, color=TEXT_SEC)
            ]))
        ], expand=True))

        asyncio.create_task(self.monitor_logs())
        await asyncio.sleep(0.2)
        try: await page.window.center()
        except: pass
        page.update()

if __name__ == "__main__":
    ft.run(NSFWLauncher().build)