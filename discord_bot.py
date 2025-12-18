from flask import jsonify
import os
import logging
from datetime import time, timezone, datetime
from bs4 import BeautifulSoup
import requests

import discord
from discord.ext import commands
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


@bot.event
async def on_ready():
    logging.info(f"Bot ready. Logged in as {bot.user} (id: {bot.user.id})")
    # start the background task only once
    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        msg = await build_message()
        await channel.send(embed=msg)
        print(f"✅ Posted leaderboard to {channel.name}")
    else:
        print("❌ Could not find the channel.")
    await bot.close()

bot.run(DISCORD_TOKEN)





