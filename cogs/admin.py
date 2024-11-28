import os
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption
from permissions import load_permissions, save_permissions
import utils
import subprocess

ADMIN_ROLE_ID = int(os.getenv('ANILY_BOT_ADMIN_ROLE_ID', 0))
CATEGORIES = os.getenv('ANILY_BOT_CATEGORIES', 'souly,anime,joni,other').split(',')
ROOT_FOLDER = os.getenv('ANILY_DDRACE_ROOT', '~/servers/ddrace')
config = utils.load_config("remote.json")

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, interaction: Interaction):
        role = nextcord.utils.get(interaction.user.roles, id=ADMIN_ROLE_ID)
        if role is None:
            await interaction.response.send_message("You don't have permission to manage map permissions.", ephemeral=True)
            return False
        return True
    
    @nextcord.slash_command(name="build_votes", description="Rebuild votes.cfg", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def build_votes(self, interaction: Interaction):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        
        subprocess.run([os.path.join(ROOT_FOLDER, f"build_votes.py")], shell=True)
        utils.run_build_votes_servers(config['servers'])

        await interaction.response.send_message("Votes were built on local and remote servers")

    @nextcord.slash_command(name="add_permission", description="Grant permission to upload/update maps", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def add_permission(self, interaction: Interaction, 
                             user: nextcord.Member = SlashOption(name="member", required=True), 
                             category: str = SlashOption(name="category", choices=CATEGORIES, required=True)):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        
        permissions = load_permissions()
        
        if str(user.id) not in permissions:
            permissions[str(user.id)] = []
        
        if category not in permissions[str(user.id)]:
            permissions[str(user.id)].append(category)
            save_permissions(permissions)
            await interaction.response.send_message(f"Permission added for user {user.mention} in category {category}.")
        else:
            await interaction.response.send_message(f"User {user.mention} already has permission for category {category}.", ephemeral=True)

    @nextcord.slash_command(name="remove_permission", description="Revoke permission to upload/update maps", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def remove_permission(self, interaction: Interaction, 
                                user: nextcord.Member = SlashOption(name="member", required=True), 
                                category: str = SlashOption(name="category", choices=CATEGORIES, required=True)):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        permissions = load_permissions()
        
        if str(user.id) in permissions and category in permissions[str(user.id)]:
            permissions[str(user.id)].remove(category)
            save_permissions(permissions)
            await interaction.response.send_message(f"Permission removed for user {user.mention} in category {category}.")
        else:
            await interaction.response.send_message(f"User {user.mention} does not have permission for category {category}.", ephemeral=True)

    @nextcord.slash_command(name="list_permissions", description="List all permissions for a user", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def list_permissions(self, 
                               interaction: Interaction, 
                               user: nextcord.Member = SlashOption(name="member", required=True)):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        permissions = load_permissions()
        
        if str(user.id) in permissions:
            categories = ", ".join(permissions[str(user.id)])
            await interaction.response.send_message(f"User {user.mention} has permissions for categories: {categories}.")
        else:
            await interaction.response.send_message(f"User {user.mention} has no permissions.")

def setup(bot):
    bot.add_cog(AdminCog(bot))
