from time import sleep

import discord
import os

from discord.ui import View, Button
import os
from discord.webhook.async_ import interaction_message_response_params
from dotenv import load_dotenv
import requests
from discord.ext import commands
import json
from discord.utils import get
import asyncio
from kurramaa_shizzz import fetch_all_player_scores
from kurramaa_shizzz import fetch_player_scores
from discord import app_commands, Interaction
from discord.ext import commands

# Set ffmpeg paths before importing convert module to prevent warnings
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
os.environ['PATH'] = os.path.join(script_dir, 'converter') + os.pathsep + os.environ['PATH']

from converter import convert

# Load environment variables
env_path = os.path.join(script_dir, "env.env")
load_dotenv(env_path)

token = os.getenv("TOKEN")

# Helper function to get absolute path for data files
def get_data_path(filename):
    return os.path.join(script_dir, filename)

emojies = [
    "<:ScoringTeamConfirmed:1408640883167068240>",
    "<:ScoringTeamDenied:1408640885650100264>",
    "<:big_gold:1408636605132181574>",
    "<:big_plastic:1408636602527514705>",
    "<:big_silver:1408636603878084689>",
    "<:diamond:1408636598253391963>",
    "<:gold:1408636599444439102>",
    "<:plastic:1408636601424150640>",
    "<:ruby:1408636596923797644>",
    "<:silver:1408636600421711902>"
]



beatleader = "https://api.beatleader.com/"
beatsaver = "https://api.beatsaver.com/"

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

class PendingScoreView(discord.ui.View):
    def __init__(self, player_alias: str, map_id: str, message: discord.Message):
        super().__init__(timeout=None)
        self.player_alias = player_alias
        self.map_id = map_id
        self.message = message  # store the message object

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # load pendingscores
        pendingscores_file = get_data_path("pendingscores.json")
        with open(pendingscores_file, "r") as f:
            pending_scores = json.load(f)

        if self.player_alias in pending_scores and self.map_id in pending_scores[self.player_alias]:
            pending_scores[self.player_alias][self.map_id]["confirmed"] = True
            with open(pendingscores_file, "w") as f:
                json.dump(pending_scores, f, indent=4)

        await interaction.response.send_message(f"✅ Score approved for {self.player_alias}!", ephemeral=True)
        await self.message.delete()  # delete the pending score message

    @discord.ui.button(label="❌ Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        # load pendingscores
        pendingscores_file = get_data_path("pendingscores.json")
        with open(pendingscores_file, "r") as f:
            pending_scores = json.load(f)

        if self.player_alias in pending_scores and self.map_id in pending_scores[self.player_alias]:
            del pending_scores[self.player_alias][self.map_id]
            if not pending_scores[self.player_alias]:
                del pending_scores[self.player_alias]

            with open(pendingscores_file, "w") as f:
                json.dump(pending_scores, f, indent=4)

        await interaction.response.send_message(f"❌ Score denied for {self.player_alias}!", ephemeral=True)
        await self.message.delete()  # delete the pending score message

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_FOLDER, "downloads")
EXPORT_FOLDER = os.path.join(BASE_FOLDER, "converted")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

class AudioCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="convert", description="Upload an MP3 and get an OGG back!")
    @app_commands.describe(
        file="The MP3 file to convert", 
        bpm="The BPM (beats per minute) of the song", 
        bars="The number of bars of silence to add to the start (default: 0)"
    )
    async def convert_command(self, interaction: discord.Interaction, file: discord.Attachment, bpm: float, bars: float = 0.0):
        # Check if commands are ready
        if not commands_ready:
            await interaction.response.send_message("Bot is still starting up, please wait a moment...", ephemeral=True)
            return
            
        # Defer immediately to prevent timeout
        await interaction.response.defer()

        if not file.filename.lower().endswith(".mp3"):
            await interaction.followup.send("Please upload an MP3 file!")
            return
            
        # Validate BPM and bars parameters
        if bpm <= 0:
            await interaction.followup.send("BPM must be greater than 0!")
            return
        if bpm > 300:  # Reasonable upper limit for BPM
            await interaction.followup.send("BPM cannot exceed 300!")
            return
        if bars < 0:
            await interaction.followup.send("Number of bars cannot be negative!")
            return
        if bars > 32:  # Reasonable limit for bars
            await interaction.followup.send("Number of bars cannot exceed 32!")
            return

        mp3_path = os.path.join(DOWNLOAD_FOLDER, file.filename)
        ogg_filename = os.path.splitext(file.filename)[0] + ".ogg"
        ogg_path = os.path.join(EXPORT_FOLDER, ogg_filename)
        print(os.path.join(EXPORT_FOLDER, ogg_filename))

        # Save the attachment
        file_bytes = await file.read()
        with open(mp3_path, "wb") as f:
            f.write(file_bytes)

        # Calculate silence duration using BPM and bars
        # Formula: 60/bpm * 4 = 1 bar in seconds * bars = silence to add in seconds
        silence_seconds = (60 / bpm * 4) * bars if bars > 0 else 0
        silence_ms = int(silence_seconds * 1000)  # Convert to milliseconds for pydub

        # Send progress message
        progress_msg = f"Converting audio file (BPM: {bpm})..."
        if bars > 0:
            progress_msg += f" (adding {bars} bars = {silence_seconds:.2f}s silence)"
        await interaction.followup.send(progress_msg)

        # Use your convert.py functionality
        try:
            convert.convert_file(mp3_path, ogg_path, silence_ms)  # Pass the specific file paths and silence
        except Exception as e:
            await interaction.followup.send(f"Conversion failed: {e}")
            # Clean up the downloaded file even if conversion failed
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
            return

        # Send OGG back with info about silence if added
        silence_info = f" (with {bars} bars = {silence_seconds:.2f}s silence added)" if bars > 0 else ""
        await interaction.followup.send(
            content=f"Converted {file.filename} to OGG{silence_info}!",
            file=discord.File(ogg_path)
        )
        
        # Clean up: delete the downloaded MP3 file to save space
        try:
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
                print(f"Cleaned up: deleted {mp3_path}")
        except Exception as e:
            print(f"Warning: Could not delete {mp3_path}: {e}")
            # Don't fail the command if cleanup fails



intents = discord.Intents.default()
intents.message_content = True

bot = MyBot()

# Add the AudioCog to the bot properly
async def setup_cogs():
    await bot.add_cog(AudioCog(bot))

# We'll call this in the on_ready event

server_settings = {}
commands_ready = False  # Flag to track if commands are ready to use
user_scans_in_progress = {}  # Dict to track scans per user



def get_medal(percent):
    if percent >= 100:
        return ":ruby:"    # max completion
    elif percent >= 90:
        return ":diamond:"
    elif percent >= 75:
        return ":gold:"
    elif percent >= 50:
        return ":silver:"
    else:
        return ":plastic:"  # low completion

@bot.event
async def on_ready():
    global commands_ready
    
    # Setup cogs first
    await setup_cogs()
    
    print(f"Logged in as {bot.user}!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
        commands_ready = True  # Mark commands as ready after successful sync
        print("Commands are now ready to use!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        commands_ready = False

    # Initialize settings for all guilds the bot is currently in
    for guild in bot.guilds:
        if guild.id not in server_settings:
            server_settings[guild.id] = {"adminchannel": "admin"}
            print(f"Initialized settings for guild: {guild.name} ({guild.id})")


bot.remove_command("help")  # Disable default help command

@bot.tree.command(name="help", description="tells you how to use the bot")
async def help(interaction: discord.Interaction):
    """Shows a list of available commands and what they do."""
    embed = discord.Embed(
        title="SSC Bot",
        description="Here’s a list of all available commands!",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🔗 Account Linking",
        value=(
            "`/link <playerid>` — Link your BeatLeader account for tracking.\n"
            "`/unlink` — Unlink your BeatLeader account.\n"
            "`/setadminchannel <channel>` — Set the admin channel for link approvals.\n"
            "`/getadminchannelname` — Check the currently set admin channel."
        ),
        inline=False
    )

    embed.add_field(
        name="📜 Map Management",
        value=(
            "`/rankmap <id> <level> <diff>` — Rank a map from BeatSaver.\n"
            "`/unrankmap <hash> <diff>` — Unrank a specific map.\n"
            "`/editmap <id> <field> <new_value>` — Edit a ranked map’s info.\n"
            "Fields: `level`, `diff`, `hash`."
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Progress & Scanning",
        value=(
            "`/scan` — Scan your BeatLeader scores and update your progress.\n"
            "`/progress` — View how much of each level you’ve cleared."
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ Other Commands",
        value=(
            "`/help` — Shows this message.\n"
        ),
        inline=False
    )

    embed.set_footer(text="BeatLeader Utility Bot • Made with 💜")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="autocreateroles", description="Automatically creates Level 1-35 roles for the server")
async def autocreateroles(interaction: discord.Interaction):
    """Creates Level 1 through Level 35 roles for the server."""
    await interaction.response.defer()
    
    guild = interaction.guild
    if not guild:
        await interaction.followup.send("This command can only be used in a server!")
        return
    
    # Check if user has manage roles permission
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.followup.send("You need 'Manage Roles' permission to use this command!")
        return
    
    created_roles = []
    existing_roles = []
    failed_roles = []
    
    await interaction.followup.send("Creating level roles... This may take a moment.")
    
    for level in range(35, 0, -1):  # 35 to 1 (reverse order for proper hierarchy)
        role_name = f"Level {level}"
        
        # Check if role already exists
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            existing_roles.append(role_name)
            continue
        
        try:
            # Create the role
            new_role = await guild.create_role(
                name=role_name,
                reason=f"Auto-created by {interaction.user.name} using /autocreateroles command"
            )
            created_roles.append(role_name)
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to create roles! Make sure my role is high enough in the hierarchy.")
            return
        except discord.HTTPException as e:
            failed_roles.append(f"{role_name} (Error: {e})")
    
    # Create summary message
    summary_parts = []
    
    if created_roles:
        summary_parts.append(f"**✅ Created {len(created_roles)} roles:**\n" + ", ".join(created_roles))
    
    if existing_roles:
        summary_parts.append(f"**⚠️ {len(existing_roles)} roles already existed:**\n" + ", ".join(existing_roles))
    
    if failed_roles:
        summary_parts.append(f"**❌ Failed to create {len(failed_roles)} roles:**\n" + ", ".join(failed_roles))
    
    if not summary_parts:
        summary_parts.append("No roles were processed.")
    
    summary = "\n\n".join(summary_parts)
    
    # Split message if too long
    if len(summary) > 2000:
        await interaction.followup.send(f"Role creation completed!\n\n**Summary:**\n- Created: {len(created_roles)} roles\n- Already existed: {len(existing_roles)} roles\n- Failed: {len(failed_roles)} roles")
    else:
        await interaction.followup.send(f"Role creation completed!\n\n{summary}")


@bot.tree.command(name="setadminchannel", description="Sets a per-server admin channel")
@app_commands.describe(channel="The channel to set as admin")
async def setadminchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id
    if guild_id not in server_settings:
        server_settings[guild_id] = {"adminchannel": "admin"}  # Initialize if not present

    server_settings[guild_id]["adminchannel"] = channel.id
    await interaction.response.send_message(f"Admin channel set to: {channel.mention}!", ephemeral=True)

@bot.tree.command(name="getadminchannel", description="gets a per-server admin channel")
async def setadminchannel(interaction: discord.Interaction):
    """Gets the per-server variable."""
    guild_id = interaction.guild.id
    if guild_id in server_settings:
        value = server_settings[guild_id]["adminchannel"]
        await interaction.response.send_message(f"admin channel: {value}", ephemeral=True)
    else:
        await interaction.response.send_message("admin channel is not set for this server yet.", ephemeral=True)

@bot.tree.command(name="unrankmap", description="unranks a map(valid diffs: Expertplus, Expert+, Expert, Hard, Normal, Easy)")
@app_commands.describe(map_id="the map id(beatsaver)", diff="the difficulty")
async def unrankmap(interaction: discord.Interaction, map_id: str, diff: str):
    if diff.lower() == "expert+":
        diff = "expertplus"

    if diff.lower() in ("expertplus", "expert", "hard", "normal", "easy"):
        pass
    else:
        await interaction.response.send_message(f"Difficulty `{diff}` is invalid! ❌")
        return
    filename = get_data_path("ranked_maps.json")
    map_hash = map_id
    if not os.path.exists(filename):
        await interaction.response.send_message("No ranked maps to remove! ⚠️ ")
        return

    # Load JSON safely
    data = {}
    try:
        with open(filename, "r") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
    except json.JSONDecodeError:
        data = {}

    found_key = None
    # Search for the map by key and difficulty
    for key, value in data.items():
        if key.strip() == map_hash.strip() and value.get("diff", "").strip().lower() == diff.strip().lower():
            found_key = key
            break

    if found_key:
        del data[found_key]  # Remove the map
        # Save updated JSON
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        await interaction.response.send_message(f"Map `{found_key}` with difficulty `{diff}` has been unranked! ✅")
    else:
        await interaction.response.send_message(f"No ranked map found with that hash and difficulty! ❌")

@bot.tree.command(name="rankmap", description="ranks a map based on its id level and diff")
async def rankmap(interaction: discord.Interaction, id: str, level: int, diff: str, adminconfirmation: bool):

    level = str(level)
    # Fetch map info from BeatSaver
    mapstats = requests.get(f"{beatsaver}/maps/id/{id}").json()
    print(mapstats)

    if mapstats.get("success", True):  # make sure the map exists
        # Normalize difficulty
        diff_lower = diff.lower()
        if diff_lower in ("expert+", "expertplus", "expert", "hard", "normal", "easy"):
            if diff_lower == "expert+":
                diff_lower = "expertplus"

            # Check if JSON file exists
            filename = get_data_path("ranked_maps.json")
            if os.path.exists(filename):
                try:
                    with open(filename, "r") as f:
                        content = f.read().strip()
                        if content:
                            data = json.loads(content)
                        else:
                            data = {}
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

            # Save the map info
            if id in data:
                await interaction.response.send_message("Map already ranked!")
                return

            data[id] = {
                "level": level,
                "diff": diff_lower,
                "name": mapstats.get("name", "Unknown"),
                "hash": mapstats.get("versions", [{}])[0].get("hash", "Unknown"),
                "adminconfirmation": adminconfirmation
            }

            # Write it back to JSON
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)

            await interaction.response.send_message(f"Map `{id}` with difficulty `{diff_lower}` saved!")
        else:
            await interaction.response.send_message("Invalid difficulty! Must be one of: Expert+, Expert, Hard, Normal, Easy.")
    else:
        await interaction.response.send_message("Map not found!")

@bot.tree.command(name="link", description="sends a link request to the mods")
@app_commands.describe(playerid="Your BeatLeader player ID or profile link")
async def link(interaction: discord.Interaction, playerid: str):
    print(playerid)
    author = interaction.user
    filename = get_data_path("Linkreq.json")

    # Extract playerid from URL if needed
    if "http" in playerid:
        if "/u/" in playerid:
            playerid = playerid.split("/u/")[1].split("/")[0]
        else:
            await interaction.response.send_message("it fucking broke it broke it broke im going insane!!!")
        print(playerid)

    # Check if valid playerid
    res = requests.get(f"{beatleader}/player/{playerid}")
    if not res.ok:
        await interaction.response.send_message("That’s not a valid player ID, silly bean!")
        return

    # Load or create Linkreq.json
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    # Load linked_players.json
    linked_players_path = get_data_path("linked_players.json")
    if os.path.exists(linked_players_path):
        try:
            with open(linked_players_path, "r") as f:
                datalinked = json.load(f)
        except json.JSONDecodeError:
            datalinked = {}
    else:
        datalinked = {}

    author_key = str(author)

    # Check if user already has a linked player
    if author_key in data or author_key in datalinked:
        await interaction.response.send_message("You already have a linked player! 😼")
        return

    # Check if player ID is already linked
    all_ids = [v["id"] for v in data.values()] + [v["id"] for v in datalinked.values()]
    if playerid in all_ids:
        await interaction.response.send_message("That player ID is already linked, silly~")
        return

    # Add or update player
    data[author_key] = {
        "user": str(author),
        "id": str(playerid),
        "uuid": author.id,
        "passedmaps": data.get(playerid, {}).get("passedmaps", {}),
    }

    # Write to JSON
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(f"`{playerid}` awaiting approval!")

    # Send request to admin channel
    guild_id = interaction.guild.id
    channel = get(interaction.guild.text_channels, name=server_settings[guild_id]["adminchannel"])

    if not channel:
        await interaction.followup.send("Uhh I couldn’t find the admin channel qwq")
        return

    msg = await channel.send(f"Link request for `{playerid}`: https://beatleader.com/u/{playerid}/ by {author.mention}")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, user):
        return (
            reaction.message.id == msg.id
            and str(reaction.emoji) in ["✅", "❌"]
            and not user.bot
        )

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=86400, check=check)

        with open(filename, "r") as f:
            linkreq_data = json.load(f)

        requester_name = str(author)
        if requester_name not in linkreq_data:
            await msg.delete()
            return

        requester = author

        if str(reaction.emoji) == "✅":
            # Approved
            linked_data = {}
            if os.path.exists(linked_players_path):
                with open(linked_players_path, "r") as f:
                    linked_data = json.load(f)

            linked_data[requester_name] = linkreq_data.pop(requester_name, None)

            with open(filename, "w") as f:
                json.dump(linkreq_data, f, indent=4)
            with open(linked_players_path, "w") as f:
                json.dump(linked_data, f, indent=4)

            await msg.delete()
            try:
                await requester.send(f"✅ Your link request (`{playerid}`) has been approved! 💖")
            except discord.Forbidden:
                await channel.send(f"Couldn’t DM {requester_name} about approval 😿")

        else:
            # Denied
            if requester_name in linkreq_data:
                del linkreq_data[requester_name]
                with open(filename, "w") as f:
                    json.dump(linkreq_data, f, indent=4)

            await msg.delete()
            try:
                await requester.send(f"❌ Your link request (`{playerid}`) was denied, sowwy qwq 💔")
            except discord.Forbidden:
                await channel.send(f"Couldn’t DM {requester_name} about denial 😿")

    except asyncio.TimeoutError:
        await channel.send("⏰ No reaction received, request expired qwq")

@bot.tree.command(
    name="editmap",
    description="Edit a ranked map by its ID, field name, and new value."
)
@app_commands.describe(
    map_id="The map ID you want to change",
    field="The field you want to edit (level, diff, or hash)",
    new_value="The new value to set for that field"
)
async def editmap(interaction: discord.Interaction, map_id: str, field: str, *, new_value: str):
    """
    Edit a ranked map's level, diff, or hash.
    Updates any linked player's passedmaps automatically.
    """
    ranked_file = get_data_path("ranked_maps.json")
    linked_file = get_data_path("linked_players.json")

    if not os.path.exists(ranked_file) or not os.path.exists(linked_file):
        await interaction.response.send_message("Required data files not found! ⚠️")
        return

    # Load ranked maps
    with open(ranked_file, "r") as f:
        try:
            ranked_data = json.load(f)
        except json.JSONDecodeError:
            await interaction.response.send_message("ranked_maps.json is corrupted! ⚠️")
            return

    if map_id not in ranked_data:
        await interaction.response.send_message(f"No map with ID `{map_id}` found! ❌")
        return

    # Load linked players
    with open(linked_file, "r") as f:
        try:
            linked_data = json.load(f)
        except json.JSONDecodeError:
            await interaction.response.send_message("linked_players.json is corrupted! ⚠️")
            return

    field = field.lower()
    if field not in ["level", "diff", "hash"]:
        await interaction.response.send_message("Field must be one of: level, diff, hash")
        return

    # Update the map itself
    if field == "level":
        try:
            new_value = int(new_value)
        except ValueError:
            await interaction.response.send_message("Level must be a number! ❌")
            return
        ranked_data[map_id]["level"] = new_value
    else:
        ranked_data[map_id][field] = new_value

    # Also update all players who have passed this map
    for user_key, user_info in linked_data.items():
        passed_maps = user_info.get("passedmaps", {})
        if map_id in passed_maps:
            if field == "level":
                passed_maps[map_id]["level"] = new_value
            else:
                passed_maps[map_id][field] = new_value

    # Save files
    with open(ranked_file, "w") as f:
        json.dump(ranked_data, f, indent=4)

    with open(linked_file, "w") as f:
        json.dump(linked_data, f, indent=4)

    await interaction.response.send_message(f"Map `{map_id}` updated: set `{field}` to `{new_value}` ✅ (all relevant players updated)")


@bot.tree.command(
    name="progress",
    description="Shows user's progress through the ranked map levels."
)
async def progress(interaction: discord.Interaction):
    """Shows user's progress through the ranked map levels."""
    linked_file = get_data_path("linked_players.json")
    ranked_file = get_data_path("ranked_maps.json")

    if not os.path.exists(linked_file):
        await interaction.response.send_message("No linked players data found! 😿")
        return
    if not os.path.exists(ranked_file):
        await interaction.response.send_message("No ranked maps found! Use !rankmap to add some first.")
        return

    # Load both files
    with open(linked_file, "r") as f:
        linked_data = json.load(f)
    with open(ranked_file, "r") as f:
        ranked_data = json.load(f)

    user_key = str(interaction.user)
    if user_key not in linked_data:
        await interaction.response.send_message("Please link your account first! ❌")
        return

    user_passed = linked_data[user_key].get("passedmaps", {})

    # Organize maps by level
    level_counts = {}
    passed_counts = {}

    for map_id, info in ranked_data.items():
        lvl = int(info.get("level", 0))
        level_counts[lvl] = level_counts.get(lvl, 0) + 1

    for map_id, info in user_passed.items():
        lvl = int(info.get("level", 0))
        passed_counts[lvl] = passed_counts.get(lvl, 0) + 1

    msg_lines = [
        f"**{interaction.user.name}'s Progress Tracker**\nHere is your current progress through the map pools:\n"]

    for lvl in sorted(level_counts.keys()):
        total = level_counts[lvl]
        passed = passed_counts.get(lvl, 0)
        percent = int((passed / total) * 100) if total > 0 else 0

        filled_blocks = int(percent / 10)
        bar = "▇" * filled_blocks + "—" * (10 - filled_blocks)

        plastic = emojies[8 - 1]
        silver = emojies[10 - 1]
        gold = emojies[7 - 1]
        diamond = emojies[6 - 1]
        ruby = emojies[9 - 1]

        if 0 <= percent <= 25:
            medal = plastic
        elif percent <= 50:
            medal = silver
        elif percent <= 75:
            medal = gold
        elif percent < 100:
            medal = diamond
        elif percent == 100:
            medal = ruby
        else:
            medal = "unknown"

        msg_lines.append(f"Lvl {lvl}: [{bar}] {percent}% :{medal}: ({passed}/{total})")

    embed = Embed(
        title=f"{interaction.user.name}'s Progress Tracker",
        description="\n".join(msg_lines),
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unlink", description="unlinks your account")
async def unlink(interaction: discord.Interaction):
    linked_file = get_data_path("linked_players.json")
    req_file = get_data_path("linkreq.json")

    # Load the JSONs
    data = {}
    datareq = {}
    if os.path.exists(linked_file):
        try:
            with open(linked_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            await interaction.response.send_message("Oops, linked_players.json is corrupted! ⚠️")
            return

    if os.path.exists(req_file):
        try:
            with open(req_file, "r") as f:
                datareq = json.load(f)
        except json.JSONDecodeError:
            await interaction.response.send_message("Oops, linkreq.json is corrupted! ⚠️")
            return

    author_key = str(interaction.user)

    # Remove from linked_players.json if present
    if author_key in data:
        del data[author_key]
        with open(linked_file, "w") as f:
            json.dump(data, f, indent=4)
        await interaction.response.send_message("Your BeatLeader account has been unlinked from linked_players.json! 💔")
        return

    # Remove from linkreq.json if present
    if author_key in datareq:
        del datareq[author_key]
        with open(req_file, "w") as f:
            json.dump(datareq, f, indent=4)
        await interaction.response.send_message("Your BeatLeader account has been unlinked from linkreq.json! 💔")
        return

    # User not found anywhere
    await interaction.response.send_message("You don't have a linked account! 😿")

from discord import Embed

import json, os, requests, asyncio
from discord import Embed
from discord import app_commands
from discord.ext import commands

import json, os, requests, asyncio
from discord import Embed
from discord import app_commands
from discord.ext import commands

@bot.tree.command(name="scores", description="View pending scores, optionally for a specific player")
@app_commands.describe(player="The player you want to see scores from")
async def scores(interaction: discord.Interaction, player: str = None):
    # Check if commands are ready
    if not commands_ready:
        await interaction.response.send_message("Bot is still starting up, please wait a moment...", ephemeral=True)
        return
        
    # Try defer first, fallback if it fails
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        # If defer fails, something is very wrong with the connection
        return

    linked_file = get_data_path("linked_players.json")
    pending_file = get_data_path("pendingscores.json")
    ranked_file = get_data_path("ranked_maps.json")

    # Load files
    with open(linked_file, "r") as f:
        linked_data = json.load(f)
    pending_scores = {}
    if os.path.exists(pending_file):
        with open(pending_file, "r") as f:
            pending_scores = json.load(f)
    with open(ranked_file, "r") as f:
        ranked_data = json.load(f)

    # Determine which players to show
    players_to_show = {}

    if player:  # single player requested
        player_lower = player.lower()
        for alias, scores in pending_scores.items():
            if alias.lower() == player_lower:
                players_to_show[alias] = scores
                break

        if not players_to_show:
            await interaction.followup.send(f"No pending scores found for player {player}! 😿")
            return
    else:  # all players
        for alias, scores in pending_scores.items():
            if scores:  # only include players who actually have pending scores
                players_to_show[alias] = scores

        if not players_to_show:
            await interaction.followup.send("No pending scores found! 😿")
            return

    # Send embeds for each pending score (only unconfirmed ones)
    for player_alias, maps in players_to_show.items():
        for map_id, info in maps.items():
            # Only show unconfirmed scores
            if info.get("confirmed", True):
                continue
                
            map_name = ranked_data.get(map_id, {}).get("name", map_id)
            diff = ranked_data.get(map_id, {}).get("diff", "Unknown").capitalize()
            replay_url = info.get("replay", "No replay available")

            embed = Embed(
                title=f"⏳ Pending Score - {player_alias}",
                description=f"**{map_name}** ({diff})\n[Replay]({replay_url})",
                color=0x1abc9c
            )

            sent_message = await interaction.followup.send(embed=embed, ephemeral=True)
            view = PendingScoreView(player_alias, map_id, sent_message)
            await sent_message.edit(view=view)



@bot.tree.command(name="scan", description="Scan your BeatLeader scores and update passed maps")
async def scan(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    # Check if commands are ready
    if not commands_ready:
        print(f"DEBUG: Commands not ready, blocking scan for user {interaction.user}")
        await interaction.response.send_message("Bot is still starting up, please wait a moment...", ephemeral=True)
        return
        
    # Check if this user already has a scan in progress
    print(f"DEBUG: Current scans in progress: {user_scans_in_progress}")
    print(f"DEBUG: Checking if user {user_id} ({interaction.user}) is in progress...")
    if user_id in user_scans_in_progress:
        print(f"DEBUG: User {interaction.user} already has scan in progress, blocking new scan")
        try:
            await interaction.response.send_message("You already have a scan in progress, please wait...", ephemeral=True)
        except:
            # If we can't respond, just ignore silently
            pass
        return
        
    user_scans_in_progress[user_id] = True
        
    # Try defer first, fallback to immediate response
    try:
        await interaction.response.defer()
        await interaction.followup.send("Scanning player scores... 🔍")
    except:
        # If defer fails, something is very wrong with the connection
        print(f"DEBUG: Defer failed for user {interaction.user}, releasing scan lock...")
        await interaction.followup.send("Something went wrong with the connection, please try again later...", ephemeral=True)
        user_scans_in_progress.pop(user_id, None)
        return

    ranked_file = get_data_path("ranked_maps.json")
    linked_file = get_data_path("linked_players.json")
    pendingscores_file = get_data_path("pendingscores.json")

    # Load linked players
    if not os.path.exists(linked_file):
        await interaction.followup.send("You haven't linked your account yet! ❌")
        user_scans_in_progress.pop(user_id, None)
        return
    with open(linked_file, "r") as f:
        linked_data = json.load(f)

    user_key = str(interaction.user)
    if user_key not in linked_data:
        await interaction.followup.send("Please link first! ❌")
        user_scans_in_progress.pop(user_id, None)
        return

    player_id = linked_data[user_key]["id"]
    print(f"DEBUG: user_key={user_key}, player_id={player_id}")

    # Load ranked maps
    if not os.path.exists(ranked_file):
        await interaction.followup.send("No ranked maps yet!")
        user_scans_in_progress.pop(user_id, None)
        return
    try:
        with open(ranked_file, "r") as f:
            ranked_data = json.load(f)
    except json.JSONDecodeError:
        await interaction.followup.send("Oops, ranked maps JSON is corrupted! ⚠️")
        user_scans_in_progress.pop(user_id, None)
        return

    if "passedmaps" not in linked_data[user_key]:
        linked_data[user_key]["passedmaps"] = {}
    user_passed = linked_data[user_key]["passedmaps"]
    print(f"DEBUG: user_passed keys = {list(user_passed.keys())}")

    # Load pending scores
    if os.path.exists(pendingscores_file):
        with open(pendingscores_file, "r") as f:
            try:
                pending_scores = json.load(f)
            except json.JSONDecodeError:
                pending_scores = {}
    else:
        pending_scores = {}
    
    # Clean up: remove any pending entries for maps that are already passed
    if player_id in pending_scores:
        maps_to_remove = []
        for map_id in pending_scores[player_id]:
            if map_id in user_passed:
                maps_to_remove.append(map_id)
                print(f"DEBUG: Removing already-passed map {map_id} from pending")
        
        for map_id in maps_to_remove:
            del pending_scores[player_id][map_id]
        
        if not pending_scores[player_id]:
            del pending_scores[player_id]
    print(f"DEBUG: pending_scores keys = {list(pending_scores.keys())}")

    new_passed_texts = []
    new_passed_count = 0

    print(f"DEBUG: Starting to process {len(ranked_data)} maps")
    for map_id, map_info in ranked_data.items():
        print(f"DEBUG: Processing map {map_id}")
        try:
            diff = map_info["diff"].capitalize()
            map_hash = map_info["hash"].upper()
            level = int(map_info.get("level", 0))
            admin_confirm = map_info.get("adminconfirmation", False)
            map_name = map_info.get("name", map_id)

            url = f"https://api.beatleader.xyz/score/0/{player_id}/{map_hash}/{diff}/Standard"
            print(url)
            resp = requests.get(url)
            if resp.status_code != 200:
                continue
            
            # Add small delay to prevent overwhelming the API
            await asyncio.sleep(0.1)
            try:
                data = resp.json()
            except requests.exceptions.JSONDecodeError:
                continue
        except Exception as e:
            print(f"ERROR processing map {map_id}: {e}")
            continue

        replayurl = data["replay"]
        score_id = replayurl.split('/')[-1].split('-')[0]
        replay = f"https://replay.beatleader.com/?scoreId={score_id}"

        mods = (data.get("modifiers") or "").upper()
        invalid_mods = {"NA", "NF", "OD", "SS", "NB", "NW"}
        if any(mod in mods for mod in invalid_mods):
            continue

        base_score = data.get("baseScore", 0)
        accuracy = data.get("accuracy", 0)
        difficulty = data.get("difficulty", {}).get("difficultyName", diff)
        song_hash = data.get("song", {}).get("hash", map_hash)

        # Initialize pending_scores structure
        if player_id not in pending_scores:
            pending_scores[player_id] = {}

        if map_id not in pending_scores[player_id] and map_id not in user_passed:
            # Only create a pending score if it doesn't exist yet AND it's not already passed
            pending_scores[player_id][map_id] = {
                "confirmed": not admin_confirm,  # auto confirm if no admin required
                "replay": replay
            }

            # Send notification **only if admin confirmation is required**
            if admin_confirm:
                channel = get(interaction.guild.text_channels, name="pending-scores")
                if channel:
                    await channel.send(
                        f"new pending score from: {interaction.user.name} "
                        f"type /scores <player> to accept their score!"
                    )
                else:
                    await interaction.followup.send("Couldn't find the pending-scores channel")

        # Check if this map exists in pending scores
        if map_id in pending_scores[player_id]:
            confirmed = pending_scores[player_id][map_id]["confirmed"]
            print(f"DEBUG: Map {map_id} in pending, confirmed={confirmed}")
        else:
            # If map is not in pending scores, it means it's already passed
            confirmed = True
            print(f"DEBUG: Map {map_id} not in pending, assuming confirmed=True")

        if confirmed:
            print(f"DEBUG: Processing confirmed map {map_id}")
            # Add to user's passed maps if not already added
            if map_id not in user_passed:
                user_passed[map_id] = {
                    "level": level,
                    "diff": difficulty,
                    "hash": song_hash,
                    "score": base_score,
                    "accuracy": accuracy,
                    "mods": mods
                }
                new_passed_texts.append(
                    f"🎵 **{map_name}** ({difficulty}) — Level: {level}, Score: {base_score}, Acc: {accuracy:.2%}"
                )
                new_passed_count += 1

            # Remove confirmed score from pending_scores
            if player_id in pending_scores and map_id in pending_scores[player_id]:
                del pending_scores[player_id][map_id]
                if not pending_scores[player_id]:
                    del pending_scores[player_id]

    # Save linked players and pending scores with error handling
    try:
        with open(linked_file, "w") as f:
            json.dump(linked_data, f, indent=4)
        print("DEBUG: Saved linked_players.json successfully")
    except Exception as e:
        print(f"ERROR: Failed to save linked_players.json: {e}")
        
    try:
        with open(pendingscores_file, "w") as f:
            json.dump(pending_scores, f, indent=4)
        print("DEBUG: Saved pendingscores.json successfully")
    except Exception as e:
        print(f"ERROR: Failed to save pendingscores.json: {e}")

    # Build pending scores display
    pending_texts = []
    if player_id in pending_scores:
        for map_id, info in pending_scores[player_id].items():
            if not info.get("confirmed", True):
                map_name = ranked_data.get(map_id, {}).get("name", map_id)
                diff = ranked_data.get(map_id, {}).get("diff", "Unknown").capitalize()
                pending_texts.append(f"⏳ **{map_name}** ({diff}) — awaiting admin approval")

    # Send embed
    print(f"DEBUG: new_passed_count={new_passed_count}, pending_texts={len(pending_texts)}")
    if new_passed_count == 0 and not pending_texts:
        print("DEBUG: Sending 'no new maps' message")
        await interaction.followup.send("You haven’t passed any new maps!")
    else:
        print("DEBUG: Sending results embed")
        description_lines = []
        if new_passed_texts:
            description_lines.append("**✅ New Maps Passed:**\n" + "\n".join(new_passed_texts))
        if pending_texts:
            description_lines.append("\n**⏳ Pending Approval:**\n" + "\n".join(pending_texts))

        embed = Embed(
            title=f"🎶 Score Scan for {interaction.user.display_name}",
            description="\n\n".join(description_lines),
            color=0x1abc9c
        )
        await interaction.followup.send(embed=embed)

    # Calculate highest level from confirmed passed maps only
    highest_level = 0
    for map_id, map_data in user_passed.items():
        level = map_data.get("level", 0)
        if level > highest_level:
            highest_level = level
    
    # Handle role assignment
    if highest_level > 0:
        level_roles = {i: f"Level {i}" for i in range(1, 36)}
        role_name = None
        for lvl, name in sorted(level_roles.items(), reverse=True):
            if highest_level >= lvl:
                role_name = name
                break

        if role_name:
            guild = interaction.guild
            member = interaction.user
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                role = await guild.create_role(name=role_name)

            for old_lvl, old_role_name in level_roles.items():
                old_role = discord.utils.get(guild.roles, name=old_role_name)
                if old_role and old_role in member.roles and old_role != role:
                    await member.remove_roles(old_role)

            await member.add_roles(role)
            await interaction.followup.send(
                f"🏅 Assigned role **{role_name}** for your highest map level: {highest_level}!"
            )
    
    print("DEBUG: Scan completed successfully!")
    print(f"DEBUG: Releasing scan lock for user {interaction.user}...")
    user_scans_in_progress.pop(user_id, None)
    print("DEBUG: Scan lock released!") 








bot.run(token)