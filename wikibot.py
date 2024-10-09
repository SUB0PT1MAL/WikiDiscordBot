import os
import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import logging
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
    '1': 'https://darksouls.wiki.fextralife.com/',
    '2': 'https://darksouls2.wiki.fextralife.com/',
    '3': 'https://darksouls3.wiki.fextralife.com/',
    'e': 'https://eldenring.wiki.fextralife.com/'
}

# Set up the headless browser with Selenium
def create_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')

    # Updated paths for Chrome and ChromeDriver
    chrome_path = "/usr/bin/google-chrome-stable"
    chromedriver_path = "/usr/local/bin/chromedriver"

    options.binary_location = chrome_path
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

async def search_wiki_selenium(wiki_key, query):
    base_url = WIKIS.get(wiki_key)
    if not base_url:
        return None, f"Invalid wiki key: {wiki_key}"

    search_url = base_url + "?q=" + query.replace(" ", "+")

    # Initialize the Selenium WebDriver
    driver = create_driver()

    try:
        # Open the search URL in the headless browser
        driver.get(search_url)
        time.sleep(2)  # Let the page load

        # Locate the first result
        result = driver.find_element_by_css_selector('a.gs-title')

        if result:
            return result.get_attribute('href'), result.text.strip()
        else:
            return None, f"No results found for '{query}' in the specified wiki."

    finally:
        driver.quit()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! I'm here and working.")

@bot.command()
async def w(ctx, wiki_key, *, query):
    url, title = await search_wiki_selenium(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    hyperlink = f"[{title}]({url})"
    await ctx.send(f"Here's the link for {hyperlink}")

@bot.command()
async def wp(ctx, wiki_key, *, query):
    url, title = await search_wiki_selenium(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    # Fetch the page content to get a summary using Selenium
    driver = create_driver()
    try:
        driver.get(url)
        time.sleep(2)  # Let the page load

        # Fetch the summary from the page
        summary = driver.find_element_by_css_selector('meta[property="og:description"]')
        summary_text = summary.get_attribute('content') if summary else "No summary available."

        # Truncate summary if it's too long
        if len(summary_text) > 200:
            summary_text = summary_text[:200] + "..."

        await ctx.send(f"**{title}**\n{summary_text}\n\n{url}")
    finally:
        driver.quit()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content
    if content.startswith('!w '):
        parts = content.split(maxsplit=2)
        if len(parts) == 3:
            wiki_key, query = parts[1], parts[2]
            url, title = await search_wiki_selenium(wiki_key, query)
            if url:
                hyperlink = f"[{title}]({url})"
                await message.channel.send(f"{message.author.mention} mentioned: {hyperlink}")
            else:
                await message.channel.send(title)  # Error message

    await bot.process_commands(message)

bot.run(BOT_TOKEN)