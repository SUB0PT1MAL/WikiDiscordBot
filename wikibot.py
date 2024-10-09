import os
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup

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
    'e': "https://eldenring.wiki.fextralife.com/Elden+Ring+Wiki#gsc.tab=0&gsc.q=",

}

async def search_wiki(wiki_key, query):
    base_url = WIKIS.get(wiki_key)
    if not base_url:
        return None, f"Invalid wiki key: {wiki_key}"

    search_url = base_url + query.replace(' ', '+')

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as response:
            if response.status != 200:
                return None, f"Error accessing the wiki: HTTP {response.status}"

            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')
    result = soup.select_one('a.gs-title')

    if not result or not result.get('href'):
        return None, f"No results found for '{query}' in the specified wiki."

    return result['href'], result.text.strip()

@bot.command()
async def w(ctx, wiki_key, *, query):
    url, title = await search_wiki(wiki_key, query)
    if not url:
        await ctx.send(title)
        return

    hyperlink = f"[{title}]({url})"
    await ctx.send(f"Here's the link for {hyperlink}")

@bot.command()
async def wp(ctx, wiki_key, *, query):
    url, title = await search_wiki(wiki_key, query)
    if not url:
        await ctx.send(title)
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