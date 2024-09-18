import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from datetime import datetime
import os
import requests
import utils
from permissions import load_permissions, has_permission

# Папка для хранения файлов карт
ROOT_FOLDER = os.getenv('ANILY_DDRACE_ROOT', '~/servers/ddrace/maps')
MAPS_FOLDER = os.path.join(ROOT_FOLDER, f"maps")

# Категории и стандартные значения
CATEGORIES = os.getenv('ANILY_BOT_CATEGORIES', 'souly,anime,joni,other').split(',')
DEFAULT_MAPPER = os.getenv('ANILY_BOT_DEFAULT_MAPPER', 'Unknown')
DEFAULT_POINTS = int(os.getenv('ANILY_BOT_DEFAULT_POINTS', 0))
DEFAULT_STARS = int(os.getenv('ANILY_BOT_DEFAULT_STARS', 1))
LOG_CHANNEL = int(os.getenv('ANILY_BOT_LOG_CHANNEL', None))
WEBHOOK_URL = os.getenv('ANILY_DDRACE_ANNMAP_WEBHOOK_URL', None)

# Проверяем, существует ли папка для карт
utils.ensure_directory_exists(MAPS_FOLDER)

class MapCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = bot.get_channel(LOG_CHANNEL)

    async def cog_check(self, ctx):
        permissions = load_permissions()
        if not has_permission(ctx.author.id, ctx.kwargs.get('category'), permissions):
            await ctx.send("You don't have permission to upload/update maps in this category.", ephemeral=True)
            return False
        return True

    @nextcord.slash_command(name="upload_map", description="Upload new map to the server")
    async def upload_map(self, interaction: Interaction, 
                         map_name: str,
                         category: str = SlashOption(choices=CATEGORIES),
                         mapper: str = DEFAULT_MAPPER, 
                         points: int = DEFAULT_POINTS, 
                         stars: int = DEFAULT_STARS, 
                         release_date: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')):
        
        permissions = load_permissions()
        if not has_permission(interaction.user.id, category, permissions):
            await interaction.response.send_message("You don't have permission to upload maps in this category.", ephemeral=True)
            return

        if not interaction.message.attachments:
            await interaction.response.send_message("Please attach .map file to the message.", ephemeral=True)
            return

        map_file = interaction.message.attachments[0]
        if not map_file.filename.endswith(".map"):
            await interaction.response.send_message("Wrong file format, .map file needed.", ephemeral=True)
            return

        # Сохранение файла
        map_path = os.path.join(MAPS_FOLDER, f"{category}/{map_name}.map")
        await utils.save_map_file(map_file, map_path)

        # Добавление карты в базу данных
        error, connection, cursor = utils.insert_map_into_db(map_name, category, points, stars, mapper, release_date)
        if error:
            await self.log_channel.send(f"Error while connecting to MySQL: {error}")
            move_error = utils.move_file_on_error(map_path, f"{MAPS_FOLDER}/errors/")
            await self.log_channel.send(move_error)
            return

        # Отправка сообщения через webhook
        stars_str = ":star:" * int(stars)
        message = f"\"**{map_name}**\" by **{mapper}** released on **{category}** {stars_str} with **{points}** points."
        data = {"content": message}
        requests.post(WEBHOOK_URL, json=data)

        # Запись в votes.cfg
        try:
            with open(f"{ROOT_FOLDER}/types/{category}/votes.cfg", "a") as vote_file:
                vote_line = f'add_vote "{map_name}" "sv_reset_file types/{category}/flexreset.cfg; change_map \\"{category}/{map_name}\\""\n'
                if category == 'other':
                    vote_line = f'add_vote "{map_name} | by {mapper}" "sv_reset_file types/{category}/flexreset.cfg; change_map \\"{category}/{map_name}\\""\n'
                vote_file.write(vote_line)
            await self.log_channel.send(f"Vote for map '{map_name}' added to '{category}' category.")
        except OSError as e:
            await self.log_channel.send(f"Error writing to votes.cfg: {e}")

        # Закрытие соединения с базой данных
        close_message = utils.close_db_connection(connection, cursor)
        if close_message:
            await self.log_channel.send(close_message)

        # Сообщение об успешной загрузке
        await interaction.response.send_message(
            f"Map '{map_name}' uploaded. Category: {category}, Mapper: {mapper}, Points: {points}, Stars: {stars}, Release date: {release_date}"
        )

    @nextcord.slash_command(name="update_map", description="Update existing map")
    async def update_map(self, interaction: Interaction, map_name: str, category: str = SlashOption(choices=CATEGORIES)):

        permissions = load_permissions()
        if not has_permission(interaction.user.id, category, permissions):
            await interaction.response.send_message("You don't have permission to update maps in this category.", ephemeral=True)
            return

        if not interaction.message.attachments:
            await interaction.response.send_message("Please attach .map file to the message.", ephemeral=True)
            return

        map_file = interaction.message.attachments[0]
        if not map_file.filename.endswith(".map"):
            await interaction.response.send_message("Wrong file format, .map file needed.", ephemeral=True)
            return

        # Путь к файлу карты
        map_path = os.path.join(MAPS_FOLDER, f"{category}/{map_name}.map")

        # Проверка существования файла
        if os.path.exists(map_path):
            await utils.save_map_file(map_file, map_path)
            await interaction.response.send_message(f"Map '{map_name}' in category '{category}' was updated.")
        else:
            await interaction.response.send_message(f"Error: Map '{map_name}' wasn't found in '{category}'.", ephemeral=True)

# Регистрация cog
def setup(bot):
    bot.add_cog(MapCog(bot))
