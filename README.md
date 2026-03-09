# NSFW-blocker-bot

[![License](https://img.shields.io/github/license/shannyo/nsfw-blocker-bot)](LICENSE)

This project is a Python Telegram bot designed to moderate NSFW content in chats it administers. It deletes detected NSFW content and records the deletions in `detect_logs.txt`.

# Installation

Install these libraries via console for the code to work:
```
pip install -U aiogram ultralytics pillow nest_asyncio
```
or for Google Colab:
```
!pip install -U aiogram ultralytics pillow nest_asyncio
```