import os
import nextcord
from nextcord.ext import commands, tasks
from nextcord import Interaction
import mysql.connector
from datetime import datetime, timedelta
import utils
import subprocess
from pytimeparse.timeparse import timeparse

MOD_ROLE_ID = int(os.getenv('ANILY_BOT_MOD_ROLE_ID', 0))
BANS_DIR = os.getenv("ANILY_DDRACE_BANS", "~/servers/ddrace/global_bans.cfg")
EXEC_ALL = os.path.join(os.getenv('ANILY_DDRACE_ROOT'), 'execute_all.sh')

class BanCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = mysql.connector.connect(
            host=os.getenv("ANILY_DDRACE_DB_HOST", "localhost"),
            database=os.getenv("ANILY_DDRACE_DB_SCHEME", "teeworlds"),
            user=os.getenv("ANILY_DDRACE_DB_USER", "teeworlds"),
            password=os.getenv("ANILY_DDRACE_DB_PASS", "bigSuperPass")
        )
        self.cursor = self.db.cursor()
        self.check_bans.start()

    async def cog_check(self, interaction: Interaction):
        role = nextcord.utils.get(interaction.user.roles, id=MOD_ROLE_ID)
        if role is None:
            await interaction.response.send_message("You don't have permission to manage bans.", ephemeral=True)
            return False
        return True

    def update_cfg(self):
        """Writes the active bans to the global-bans.cfg file."""
        self.cursor.execute("SELECT Nickname, IP, Reason, CONCAT('[UTC] Ends ', DATE_FORMAT(CONVERT_TZ(UnbanTime, @@session.time_zone, '+00:00'), '%d %b. %Y')) AS BanEnd FROM bans WHERE UnbanTime > NOW() OR UnbanTime IS NULL")
        active_bans = self.cursor.fetchall()

        with open(BANS_DIR, "w") as cfg:
            cfg.write(f"unban_all\n")
            for ban in active_bans:
                nickname, ip, reason, ban_end = ban
                cfg.write(f"ban {ip} -1 {reason}. {ban_end}\n")

        config = utils.load_config('remote.json')
        utils.upload_bans_to_servers(config['servers'], BANS_DIR, os.path.basename(BANS_DIR))

        self.execute_on_servers()

    def execute_on_servers(self):
        config = utils.load_config('remote.json')
        command = "exec " + os.path.basename(BANS_DIR)
        subprocess.call([EXEC_ALL, command])
        utils.run_execute_all_servers(config['servers'], command)

    @tasks.loop(seconds=30)
    async def check_bans(self):
        """Check for expired bans and remove them."""
        self.cursor.execute("SELECT Nickname, IP FROM bans WHERE UnbanTime <= NOW()")
        expired_bans = self.cursor.fetchall()

        if expired_bans:
            for ban in expired_bans:
                nickname, ip = ban
                self.cursor.execute("DELETE FROM bans WHERE Nickname=%s AND IP=%s", (nickname, ip))
            
            self.db.commit()
            self.update_cfg()

    @nextcord.slash_command(name="ban", description="Ban a player", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def ban(self, interaction: nextcord.Interaction, 
                  nickname: str, 
                  ip: str, 
                  time_str: str,
                  reason: str = "No reason provided"):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        
        unban_time = None
        minutes = int(timeparse(time_str)/60)
        if minutes:
            unban_time = datetime.now() + timedelta(minutes=minutes)

        self.cursor.execute(
            "INSERT INTO bans (Nickname, IP, Reason, UnbanTime) VALUES (%s, %s, %s, %s)",
            (nickname, ip, reason, unban_time)
        )
        self.db.commit()
        self.update_cfg()

        await interaction.response.send_message(f"Player {nickname} ({ip}) banned for {minutes} minutes. Ban ends <t:{round(unban_time.timestamp())}:R>." if minutes else f"Player {nickname} ({ip}) banned permanently.")

    @nextcord.slash_command(name="unban_all", description="Unban all players", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def unban_all(self, interaction: nextcord.Interaction):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        
        self.cursor.execute("DELETE FROM bans")
        self.db.commit()
        self.update_cfg()

        await interaction.response.send_message("All bans removed and servers updated.")

    @nextcord.slash_command(name="unban", description="Unban ip", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def unban(self, interaction: nextcord.Interaction, ip: str):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        
        self.cursor.execute("DELETE FROM bans WHERE IP = %s", (ip,))
        self.db.commit()
        self.update_cfg()

        await interaction.response.send_message(f"Ban for {ip} removed and servers updated.")

    @nextcord.slash_command(name="ban_list", description="Get the list of all active bans", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def ban_list(self, interaction: nextcord.Interaction):
        has_perm = await self.cog_check(interaction)
        if not has_perm:
            return
        
        self.cursor.execute("SELECT Nickname, IP, Reason, UnbanTime FROM bans WHERE UnbanTime > NOW() OR UnbanTime IS NULL")
        active_bans = self.cursor.fetchall()

        if not active_bans:
            await interaction.response.send_message("No active bans.")
        else:
            message = "\n".join([f"Player: {ban[0]}, IP: {ban[1]}, Reason: {ban[2]}, Unban Time(UTC): {ban[3] if ban[3] else 'Permanent'}" for ban in active_bans])
            await interaction.response.send_message(message)

    @commands.Cog.listener()
    async def on_ready(self):
        self.check_bans.start()

    def cog_unload(self):
        self.check_bans.cancel()

def setup(bot):
    bot.add_cog(BanCog(bot))
