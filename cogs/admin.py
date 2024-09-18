import os
import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from utils import load_permissions, save_permissions

ADMIN_ROLE_ID = int(os.getenv('ANILY_BOT_ADMIN_ROLE_ID', 0))

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, interaction: Interaction):
        role = nextcord.utils.get(interaction.user.roles, id=ADMIN_ROLE_ID)
        if role is None:
            await interaction.response.send_message("You don't have permission to manage map permissions.", ephemeral=True)
            return False
        return True

    @nextcord.slash_command(name="add_permission", description="Grant permission to upload/update maps")
    async def add_permission(self, interaction: Interaction, user_id: int, category: str):
        permissions = load_permissions()
        
        if str(user_id) not in permissions:
            permissions[str(user_id)] = []
        
        if category not in permissions[str(user_id)]:
            permissions[str(user_id)].append(category)
            save_permissions(permissions)
            await interaction.response.send_message(f"Permission added for user {user_id} in category {category}.")
        else:
            await interaction.response.send_message(f"User {user_id} already has permission for category {category}.", ephemeral=True)

    @nextcord.slash_command(name="remove_permission", description="Revoke permission to upload/update maps")
    async def remove_permission(self, interaction: Interaction, user_id: int, category: str):
        permissions = load_permissions()
        
        if str(user_id) in permissions and category in permissions[str(user_id)]:
            permissions[str(user_id)].remove(category)
            save_permissions(permissions)
            await interaction.response.send_message(f"Permission removed for user {user_id} in category {category}.")
        else:
            await interaction.response.send_message(f"User {user_id} does not have permission for category {category}.", ephemeral=True)

    @nextcord.slash_command(name="list_permissions", description="List all permissions for a user")
    async def list_permissions(self, interaction: Interaction, user_id: int):
        permissions = load_permissions()
        
        if str(user_id) in permissions:
            categories = ", ".join(permissions[str(user_id)])
            await interaction.response.send_message(f"User {user_id} has permissions for categories: {categories}.")
        else:
            await interaction.response.send_message(f"User {user_id} has no permissions.", ephemeral=True)

# Setup
def setup(bot):
    bot.add_cog(AdminCog(bot))
