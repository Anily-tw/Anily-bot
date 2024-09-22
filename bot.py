#!/bin/env python3
import nextcord
from nextcord.ext import commands
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    bot.load_extension("cogs.maps")
    bot.load_extension("cogs.admin")
    bot.load_extension("cogs.stats")
    await bot.discover_application_commands()
    await bot.sync_all_application_commands()
    logger.info(f"{len(bot.get_all_application_commands())} slash commands are synced")

bot.run(os.getenv("ANILY_BOT_TOKEN"))
