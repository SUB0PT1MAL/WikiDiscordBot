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
import asyncio
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

class WebDriverManager:
    def __init__(self):
        self.driver = None
        self.lock = asyncio.Lock()

    async def get_driver(self):
        async with self.lock:
            if self.driver is None:
                options = Options()
                options.add_argument('-headless')
                service = Service(executable_path="/usr/local/bin/geckodriver")
                self.driver = webdriver.Firefox(service=service, options=options)
            return self.driver

    async def close(self):
        async with self.lock:
            if self.driver:
                self.driver.quit()
                self.driver = None

driver_manager = WebDriverManager()

def run_in_executor(func):
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    return wrapper

@run_in_executor
def perform_selenium_search(driver, search_url):
    driver.get(search_url)
    try:
        result = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.g a'))
        )
        return result.get_attribute('href'), result.text.strip()
    except (TimeoutException, NoSuchElementException):
        return None, None

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

    domain = base_url.split('//')[1].split('/')[0]
    search_url = f"https://www.google.com/search?q=site%3A{domain}+{query.replace(' ', '+')}"

    driver = await driver_manager.get_driver()
    url, title = await perform_selenium_search(driver, search_url)

    if url and title:
        return url, title
    else:
        return None, f"No results found for '{query}' in the specified wiki."

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot has the following permissions: {bot.user.guild_permissions.value}')
    await driver_manager.get_driver()

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! I'm here and working.")

@bot.command()
async def wp(ctx, wiki_key, *, query):
    url, title = await search_wiki_selenium(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    driver = await driver_manager.get_driver()
    try:
        summary_text = await get_page_summary(driver, url)
        if len(summary_text) > 200:
            summary_text = summary_text[:200] + "..."

        await ctx.send(f"**{title}**\n{summary_text}\n\n{url}")
    except Exception as e:
        logging.error(f"Error fetching page content: {str(e)}")
        await ctx.send(f"An error occurred while fetching the page content for '{query}'")

@bot.command()
async def w(ctx, wiki_key, *, query):
    url, title = await search_wiki_selenium(wiki_key, query)
    if not url:
        await ctx.send(title)  # In this case, title contains the error message
        return

    hyperlink = f"[{title}]({url})"
    await ctx.send(f"Here's the link for {hyperlink}")

@run_in_executor
def get_page_summary(driver, url):
    driver.get(url)
    try:
        summary = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'meta[property="og:description"]'))
        )
        return summary.get_attribute('content') if summary else "No summary available."
    except (TimeoutException, NoSuchElementException):
        return "No summary available."

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    w_pattern = r'!w\s+(\d+)\s+"(.*?)"'
    wp_pattern = r'!wp\s+(\d+)\s+"(.*?)"'
    
    w_matches = re.findall(w_pattern, message.content)
    wp_matches = re.findall(wp_pattern, message.content)

    if w_matches:
        replacements = []
        for match in w_matches:
            key, search_term = match
            url, title = await search_wiki_selenium(key, search_term)
            if url and title:
                hyperlink = f"[{title}]({url})"
                replacements.append((f'!w {key} "{search_term}"', hyperlink))
            else:
                replacements.append((f'!w {key} "{search_term}"', f"No results found for '{search_term}'"))

        new_content = message.content
        for old, new in replacements:
            new_content = new_content.replace(old, new)

        try:
            await message.edit(content=new_content)
        except discord.Forbidden:
            await message.channel.send("I don't have permission to edit messages. Please grant me the 'Manage Messages' permission.")
        except discord.HTTPException:
            await message.channel.send("An error occurred while trying to edit the message.")

    if wp_matches:
        driver = await driver_manager.get_driver()
        for match in wp_matches:
            key, search_term = match
            url, title = await search_wiki_selenium(key, search_term)
            if url and title:
                try:
                    summary_text = await get_page_summary(driver, url)
                    if len(summary_text) > 200:
                        summary_text = summary_text[:200] + "..."
                    await message.channel.send(f"**{title}**\n{summary_text}\n\n{url}")
                except Exception as e:
                    logging.error(f"Error fetching page content: {str(e)}")
                    await message.channel.send(f"An error occurred while fetching the page content for '{search_term}'")
            else:
                await message.channel.send(f"No results found for '{search_term}' in the specified wiki.")

    await bot.process_commands(message)

        
bot.run(BOT_TOKEN)