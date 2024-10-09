import os
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import logging
import asyncio
import time

logging.basicConfig(level=logging.DEBUG)

BOT_TOKEN = os.environ['BOT_TOKEN']

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Dictionary to store wiki configurations
WIKIS = {
    '1': "https://darksouls.wiki.fextralife.com/Dark+Souls+Wiki#gsc.tab=0&gsc.q=",
    '2': "https://darksouls2.wiki.fextralife.com/Dark+Souls+2+Wiki#gsc.tab=0&gsc.q=",
    '3': "https://darksouls3.wiki.fextralife.com/Dark+Souls+2+Wiki#gsc.tab=0&gsc.q=",
    'e': "https://eldenring.wiki.fextralife.com/Elden+Ring+Wiki#gsc.tab=0&gsc.q="
}

# Rate limiting
RATE_LIMIT = 1  # One request per second
last_request_time = 0

async def search_wiki(wiki_key, query):
    global last_request_time
    base_url = WIKIS.get(wiki_key)
    if not base_url:
        return None, f"Invalid wiki key: {wiki_key}"

    search_url = base_url + query.replace(' ', '+')

    # Implement rate limiting
    current_time = asyncio.get_event_loop().time()
    if current_time - last_request_time < RATE_LIMIT:
        await asyncio.sleep(RATE_LIMIT - (current_time - last_request_time))
    last_request_time = asyncio.get_event_loop().time()

    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1',  # Do Not Track
    'Referer': 'https://google.com/',  # Sometimes adding a referer helps
    }

    async with aiohttp.ClientSession(headers=headers) as session:
    async with session.get(search_url) as response:
        if response.status != 200:
            return None, f"Error accessing the wiki: HTTP {response.status}"
        html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')
    result = soup.select_one('a.gs-title')

    if not result or not result.get('href'):
        return None, f"No results found for '{query}' in the specified wiki."

    return result['href'], result.text.strip()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! I'm here and working.")

@bot.command()
async def w(ctx, wiki_key, *, query):
    url, title = await search_wiki(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    hyperlink = f"[{title}]({url})"
    await ctx.send(f"Here's the link for {hyperlink}")

@bot.command()
async def wp(ctx, wiki_key, *, query):
    url, title = await search_wiki(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    # Fetch the page content to get a summary
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send(f"Error fetching page content: HTTP {response.status}")
                return
            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')
    summary = soup.find('meta', property='og:description')
    summary_text = summary['content'] if summary else "No summary available."

    # Truncate summary if it's too long
    if len(summary_text) > 200:
        summary_text = summary_text[:200] + "..."

    await ctx.send(f"**{title}**\n{summary_text}\n\n{url}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content
    if content.startswith('!w '):
        parts = content.split(maxsplit=2)
        if len(parts) == 3:
            wiki_key, query = parts[1], parts[2]
            url, title = await search_wiki(wiki_key, query)
            if url:
                hyperlink = f"[{title}]({url})"
                await message.channel.send(f"{message.author.mention} mentioned: {hyperlink}")
            else:
                await message.channel.send(title)  # Error message

    await bot.process_commands(message)

bot.run(BOT_TOKEN)