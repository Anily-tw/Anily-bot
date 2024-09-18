#!/bin/env python3
import nextcord
from nextcord.ext import commands
import os

intents = nextcord.Intents.default()
bot = commands.Bot(command_prefix="%", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.load_extension("cogs.maps")
    await bot.load_extension("cogs.admin")

# Запуск бота
bot.run(os.getenv("ANILY_BOT_TOKEN"))
