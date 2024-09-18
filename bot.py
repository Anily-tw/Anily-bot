#!/bin/env python3
import nextcord
from nextcord.ext import commands
import os

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.load_extension("cogs.maps")
    bot.load_extension("cogs.admin")
    await bot.sync_all_application_commands()
    print("Slash commands are synced")

bot.run(os.getenv("ANILY_BOT_TOKEN"))
