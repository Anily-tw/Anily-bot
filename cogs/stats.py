import mysql.connector
from mysql.connector import Error
import nextcord
from nextcord import SlashOption
from nextcord.ext import commands
import os

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connection = None
        self.connect_db()

    def connect_db(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.getenv("ANILY_DDRACE_DB_HOST", "localhost"),
                database=os.getenv("ANILY_DDRACE_DB_SCHEME", "teeworlds"),
                user=os.getenv("ANILY_DDRACE_DB_USER", "teeworlds"),
                password=os.getenv("ANILY_DDRACE_DB_PASS", "bigSuperPass")
            )
        except Error as e:
            print(f"Error while connecting to MySQL: {e}")
    
    def close_db(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    @nextcord.slash_command(name="top_players", description="Get top players by points", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def top_players(self, interaction: nextcord.Interaction):
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT Name, Points FROM record_points ORDER BY Points DESC LIMIT 10;")
            result = cursor.fetchall()

            embed = nextcord.Embed(
                title=f"Top 10 Players",
                color=nextcord.Color.blue(),
                description=""
            )

            if result:
                for player in result:
                    embed.description += f"{player['Name']} - {player['Points']} points\n"
            else:
                embed.title = "No Players Found"

            await interaction.response.send_message(embed=embed)

        except Error as e:
            await interaction.response.send_message(f"Error fetching top players: {e}")

    @nextcord.slash_command(name="player_stats", description="Get stats of a specific player", guild_ids=[os.getenv('ANILY_BOT_GUILD')])
    async def player_stats(self, interaction: nextcord.Interaction, 
                           player_name: str = SlashOption(name="player_name", required=True)):
        try:
            cursor = self.connection.cursor(dictionary=True)

            points_query = """
                SELECT Points
                FROM record_points
                WHERE Name = %s
            """
            cursor.execute(points_query, (player_name,))
            points_result = cursor.fetchone()
            points = points_result["Points"] if points_result else 0

            completed_maps_query = """
                SELECT COUNT(DISTINCT Map) AS CompletedMaps
                FROM record_race
                WHERE Name = %s
            """
            cursor.execute(completed_maps_query, (player_name,))
            completed_maps_result = cursor.fetchone()
            completed_maps = completed_maps_result["CompletedMaps"] if completed_maps_result else 0

            last_maps_query = """
                SELECT Map, Time, Timestamp
                FROM record_race
                WHERE Name = %s
                ORDER BY Timestamp DESC
                LIMIT 3
            """
            cursor.execute(last_maps_query, (player_name,))
            last_maps = cursor.fetchall()

            if last_maps:
                last_maps_list = "\n".join([f"{record['Map']} - {record['Time']} seconds on {record['Timestamp']}" for record in last_maps])
            else:
                last_maps_list = "No maps completed."

            embed = nextcord.Embed(
                title=f"Stats for {player_name}",
                color=nextcord.Color.blue()
            )
            embed.add_field(name="Points", value=str(points), inline=False)
            embed.add_field(name="Completed Maps", value=str(completed_maps), inline=False)
            embed.add_field(name="Last 3 Completed Maps", value=last_maps_list, inline=False)

            await interaction.response.send_message(embed=embed)
        except Error as e:
            await interaction.response.send_message(f"Error fetching top players: {e}")

def setup(bot):
    bot.add_cog(StatsCog(bot))
