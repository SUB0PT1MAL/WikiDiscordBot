import os
import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import time
import subprocess
import sys
import re

logging.basicConfig(level=logging.DEBUG)

BOT_TOKEN = os.environ['BOT_TOKEN']

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Dictionary to store wiki configurations
WIKIS = {
    '1': 'https://darksouls.wiki.fextralife.com/',
    '2': 'https://darksouls2.wiki.fextralife.com/',
    '3': 'https://darksouls3.wiki.fextralife.com/',
    'e': 'https://eldenring.wiki.fextralife.com/'
}

# Set up the headless browser with Selenium
def create_driver():
    logging.debug("Creating WebDriver...")
    options = Options()
    options.add_argument('-headless')

    geckodriver_path = "/usr/local/bin/geckodriver"

    logging.debug(f"Geckodriver path: {geckodriver_path}")

    # Log Firefox and geckodriver versions
    try:
        firefox_version = subprocess.check_output(['firefox', '--version']).decode('utf-8').strip()
        geckodriver_version = subprocess.check_output([geckodriver_path, '--version']).decode('utf-8').strip()
        logging.debug(f"Firefox version: {firefox_version}")
        logging.debug(f"Geckodriver version: {geckodriver_version}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error getting version info: {e}")
        logging.error(f"Firefox or geckodriver might not be installed correctly.")
        sys.exit(1)

    service = Service(executable_path=geckodriver_path)
    
    try:
        driver = webdriver.Firefox(service=service, options=options)
        logging.debug("WebDriver created successfully")
        return driver
    except Exception as e:
        logging.error(f"Error creating WebDriver: {str(e)}")
        logging.error("Firefox and geckodriver versions:")
        logging.error(f"Firefox: {firefox_version}")
        logging.error(f"Geckodriver: {geckodriver_version}")
        raise

from selenium.webdriver.common.by import By

async def search_wiki_selenium(wiki_key, query):
    base_url = WIKIS.get(wiki_key)
    if not base_url:
        return None, f"Invalid wiki key: {wiki_key}"

    # Extract the domain from the base_url
    domain = base_url.split('//')[1].split('/')[0]
    
    # Construct the Google search URL with site filter
    search_url = f"https://www.google.com/search?q=site%3A{domain}+{query.replace(' ', '+')}"

    driver = create_driver()

    try:
        driver.get(search_url)
        
        logging.debug(f"Page title: {driver.title}")
        logging.debug(f"Current URL: {driver.current_url}")
        
        try:
            # Wait for up to 2 seconds for the search results to be present
            result = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g a'))
            )
            return result.get_attribute('href'), result.text.strip()
        except TimeoutException:
            print("Timeout waiting for Google search results. Page source:")
            print(driver.page_source)
            return None, f"No results found for '{query}' in the specified wiki."
        except NoSuchElementException:
            print("Search results not found. Page source:")
            print(driver.page_source)
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
async def wp(ctx, wiki_key, *, query):
    url, title = await search_wiki_selenium(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    driver = create_driver()
    try:
        driver.get(url)
        
        try:
            summary = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:description"]'))
            )
            summary_text = summary.get_attribute('content') if summary else "No summary available."
        except (TimeoutException, NoSuchElementException):
            summary_text = "No summary available."

        # Truncate summary if it's too long
        if len(summary_text) > 200:
            summary_text = summary_text[:200] + "..."

        await ctx.send(f"**{title}**\n{summary_text}\n\n{url}")
    finally:
        driver.quit()

@bot.command()
async def w(ctx, *args):
    # Combine the message back into a single string
    message_content = ' '.join(args)

    # Use regular expression to extract the command format !w <key> "quoted text"
    pattern = r'!w (\d+) "(.*?)"'
    match = re.search(pattern, message_content)

    if match:
        # Extract the key (e.g., 1) and the quoted text (e.g., "war hammer")
        wiki_key = match.group(1)
        search_term = match.group(2)

        # Check if the key is valid in WIKIS dictionary
        if wiki_key in WIKIS:
            wiki_url = WIKIS[wiki_key]
            # Perform your logic with the extracted data (e.g., wiki search)
            await ctx.send(f'Searching for "{search_term}" in the wiki: {wiki_url}')
        else:
            await ctx.send(f'Invalid wiki key: {wiki_key}')
    else:
        await ctx.send('Invalid command format. Use: !w <wiki_key> "<search_term>"')

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
                hyperlink = f"[{query}]({url})"
                try:
                    await message.edit(content=hyperlink)
                except discord.errors.Forbidden:
                    await message.channel.send(f"{message.author.mention} mentioned: {hyperlink}")
            else:
                await message.channel.send(title)  # Error message

    await bot.process_commands(message)

bot.run(BOT_TOKEN)