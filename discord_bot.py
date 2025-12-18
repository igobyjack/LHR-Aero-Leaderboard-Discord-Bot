from flask import jsonify
import os
import logging
from datetime import time, timezone, datetime
from bs4 import BeautifulSoup
import requests

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

#Config
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
if not DISCORD_TOKEN or CHANNEL_ID == 0:
    raise RuntimeError("DISCORD_TOKEN and LEADERBOARD_CHANNEL_ID must be set as env vars")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)

async def get_leaderboard_details():
    try:
        url = 'https://lhr.symbolstrade.com/'
        res = requests.get(url)
        html_txt = res.text
        soup = BeautifulSoup(html_txt, 'html.parser')
        rankers = soup.select('.ranking .ranker p')
        out = {}
        rank = 1
        for i in range(0, len(rankers), 2):
            print((rankers[i].text, rankers[i+1].text))
            out[str(rank)] = (rankers[i].text, rankers[i+1].text) # name, xp
            rank += 1
        
        return out
    except Exception as e:
        return "Error Getting Leaderboard", 404
    
async def build_message():
    leaderboard = await get_leaderboard_details()

    embed = discord.Embed(
        title="LHR Aero Leaderboard",
        description="**(Rank, Name, XP)**",
        color=discord.Color.blue()
    )

    ranks = list(leaderboard.keys())
    for i in range(len(ranks)):
        ranks[i] = int(ranks[i])
    ranks.sort()

    for rank in ranks:
        name, xp = leaderboard[str(rank)]
        embed.add_field(name=f"#{rank} {name}", value=f"{xp} XP", inline=False)
    return embed

def detect_changes(old_leaderboard, new_leaderboard):
    changes = []
    
    old_by_name = {name: xp for rank, (name, xp) in old_leaderboard.items()}
    new_by_name = {name: xp for rank, (name, xp) in new_leaderboard. items()}
    
    for name, new_xp in new_by_name. items():
        if name in old_by_name:
            old_xp = old_by_name[name]
            if old_xp != new_xp: 
                changes.append({
                    "name": name,
                    "old_xp": old_xp,
                    "new_xp": new_xp
                })
        else:
            changes.append({
                "name":  name,
                "old_xp": None,
                "new_xp": new_xp
            })
    
    return changes

@tasks.loop(seconds=30)
async def check_leaderboard():
    global previous_leaderboard
    
    logging.info("Checking leaderboard for changes...")
    
    current_leaderboard = await get_leaderboard_details()
    
    if isinstance(current_leaderboard, tuple):
        logging.error("Failed to fetch leaderboard")
        return
    
    if not previous_leaderboard:
        previous_leaderboard = current_leaderboard
        logging.info("Initial leaderboard state stored")
        return
    
    # Detect changes
    changes = detect_changes(previous_leaderboard, current_leaderboard)
    
    if changes: 
        # Get the aero channel (fallback to main channel if not set)
        channel_id = AERO_CHANNEL_ID if AERO_CHANNEL_ID != 0 else CHANNEL_ID
        channel = bot.get_channel(channel_id)
        
        if channel:
            for change in changes: 
                if change["old_xp"] is None:
                    # New player
                    message = f"**{change['name']}** has joined"
                else:
                    # XP changed
                    message = f"**{change['name']}** has submitted a job, good boyyy"
                
                await channel.send(message)
                logging.info(f"Sent change notification:  {message}")
        else:
            logging.error("Could not find the aero channel")
    
    # Update the stored leaderboard
    previous_leaderboard = current_leaderboard


@check_leaderboard. before_loop
async def before_check_leaderboard():
    await bot.wait_until_ready()



@bot.event
async def on_ready():
    logging.info(f"Bot ready.  Logged in as {bot.user} (id: {bot. user.id})")
    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        msg = await build_message()
        await channel.send(embed=msg)
        print(f"✅ Posted leaderboard to {channel.name}")
    else:
        print("❌ Could not find the channel.")
    
    if not check_leaderboard. is_running():
        check_leaderboard.start()
        logging.info("Started leaderboard monitoring task (every 30 seconds)")

bot.run(DISCORD_TOKEN)





