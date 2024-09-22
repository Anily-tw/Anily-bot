import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from datetime import datetime
import os
import requests
import utils
from typing import Optional
from permissions import load_permissions, has_permission

ROOT_FOLDER = os.getenv('ANILY_DDRACE_ROOT', '~/servers/ddrace/maps')
MAPS_FOLDER = os.path.join(ROOT_FOLDER, f"maps")

CATEGORIES = os.getenv('ANILY_BOT_CATEGORIES', 'souly,anime,joni,other').split(',')
DEFAULT_MAPPER = os.getenv('ANILY_BOT_DEFAULT_MAPPER', 'Unknown')
DEFAULT_POINTS = int(os.getenv('ANILY_BOT_DEFAULT_POINTS', 0))
DEFAULT_STARS = int(os.getenv('ANILY_BOT_DEFAULT_STARS', 1))
LOG_CHANNEL = int(os.getenv('ANILY_BOT_LOG_CHANNEL', None))
WEBHOOK_URL = os.getenv('ANILY_DDRACE_ANNMAP_WEBHOOK_URL', None)

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

    @nextcord.slash_command(name="upload_map", description="Upload new map to the server", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def upload_map(self, interaction: Interaction, 
                         map_file: nextcord.Attachment = SlashOption(name="map", description="File", required=True),
                         map_name: str = SlashOption(name="map_name", description="Name of map", required=True),
                         category: str = SlashOption(name="category", choices=CATEGORIES, required=True),
                         mapper: str = SlashOption(name="mapper", required=True, default=DEFAULT_MAPPER), 
                         points: int = SlashOption(name="points", required=True, default=DEFAULT_POINTS, min_value=0), 
                         stars: int = SlashOption(name="stars", required=True, default=DEFAULT_STARS, min_value=1, max_value=5), 
                         release_date: Optional[str] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')):
        
        permissions = load_permissions()
        if not has_permission(interaction.user.id, category, permissions):
            await interaction.response.send_message("You don't have permission to upload maps in this category.", ephemeral=True)
            return

        if not map_file:
            await interaction.response.send_message("Please attach .map file to the message.", ephemeral=True)
            return

        if not map_file.filename.endswith(".map"):
            await interaction.response.send_message("Wrong file format, .map file needed.", ephemeral=True)
            return

        map_path = os.path.join(MAPS_FOLDER, f"{category}/{map_name}.map")
        await utils.save_map_file(map_file, map_path)

        config = utils.load_config("remote.json")
        utils.upload_map_to_servers(config['servers'], map_path, f"{category}/{map_name}.map")

        if category != 'test':
            error, connection, cursor = utils.insert_map_into_db(map_name, category, points, stars, mapper, release_date)
            if error:
                await self.log_channel.send(f"Error while connecting to MySQL: {error}")
                move_error = utils.move_file_on_error(map_path, f"{MAPS_FOLDER}/errors/")
                await self.log_channel.send(move_error)
                return

            stars_str = ":star:" * int(stars)
            message = f"\"**{map_name}**\" by **{mapper}** released on **{category}** {stars_str} with **{points}** points."
            data = {"content": message}
            requests.post(WEBHOOK_URL, json=data)

        try:
            with open(f"{ROOT_FOLDER}/types/{category}/votes.cfg", "a") as vote_file:
                vote_line = f'add_vote "{map_name}" "sv_reset_file types/{category}/flexreset.cfg; change_map \\"{category}/{map_name}\\""\n'
                if category == 'other' or category == 'test':
                    vote_line = f'add_vote "{map_name} | by {mapper}" "sv_reset_file types/{category}/flexreset.cfg; change_map \\"{category}/{map_name}\\""\n'
                vote_file.write(vote_line)
            await self.log_channel.send(f"Vote for map '{map_name}' added to '{category}' category.")
        except OSError as e:
            await self.log_channel.send(f"Error writing to votes.cfg: {e}")

        if category != 'test':
            close_message = utils.close_db_connection(connection, cursor)
            if close_message:
                await self.log_channel.send(close_message)
            exec(open(os.path.join(ROOT_FOLDER, f"build_votes.py")).read())
            utils.run_build_votes_servers(config['servers'])
        await interaction.response.send_message(
            f"Map '{map_name}' uploaded. Category: '{category}', Mapper: '{mapper}', Points: {points}, Stars: {stars}, Release date: {release_date}"
        )

    @nextcord.slash_command(name="get_map", description="Download current version of the map", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def get_map(self, interaction: Interaction, 
                         map_name: str = SlashOption(name="map_name", description="Name of map", required=True),
                         category: str = SlashOption(name="category", choices=CATEGORIES, required=True)):
        
        map_path = os.path.join(MAPS_FOLDER, f"{category}/{map_name}.map")

        if utils.file_exists(map_path):
            await interaction.response.send_message(
                f"Map '{map_name}'. Category: {category}", file=nextcord.File(open(map_path, "rb"))
            )
        else:
            await interaction.response.send_message(
                f"Map '{map_name}' doesn't exist in '{category}'"
            )

    @nextcord.slash_command(name="update_map", description="Update existing map", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def update_map(self, interaction: Interaction, 
                         map_file: nextcord.Attachment = SlashOption(name="map", description="File", required=True),
                         map_name: str = SlashOption(name="map_name", description="Name of map displayed in votes", required=True), 
                         category: str = SlashOption(name="category", choices=CATEGORIES, required=True)):

        permissions = load_permissions()
        if not has_permission(interaction.user.id, category, permissions):
            await interaction.response.send_message("You don't have permission to update maps in this category.", ephemeral=True)
            return

        if not map_file:
            await interaction.response.send_message("Please attach .map file to the message.", ephemeral=True)
            return

        if not map_file.filename.endswith(".map"):
            await interaction.response.send_message("Wrong file format, .map file needed.", ephemeral=True)
            return

        map_path = os.path.join(MAPS_FOLDER, f"{category}/{map_name}.map")

        if os.path.exists(map_path):
            await utils.save_map_file(map_file, map_path)
            await interaction.response.send_message(f"Map '{map_name}' in category '{category}' was updated.")
        else:
            await interaction.response.send_message(f"Error: Map '{map_name}' wasn't found in '{category}'.", ephemeral=True)

def setup(bot):
    bot.add_cog(MapCog(bot))
