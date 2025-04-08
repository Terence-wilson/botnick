import discord
import random
import asyncio
from discord.ext import commands
import os

TITLE_FILE = "used_titles.txt"

def load_used_titles():
    if not os.path.exists(TITLE_FILE):
        return set()
    with open(TITLE_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_used_title(title):
    with open(TITLE_FILE, "a") as f:
        f.write(f"{title}\n")


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Word pools
def load_words_from_file(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as file:
        words = file.read().splitlines()
    return words

modifiers = load_words_from_file("modifiers.txt")  # Load modifiers from file
nouns = load_words_from_file("nouns.txt")  # Load nouns from file


used_titles = load_used_titles()
  # Store used "Modifier Noun" combos

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')

async def run_title_sequence(member, channel_log, redirect_channel):
    try:
        # Generate 5 unique options not already used
        options = []
        attempts = 0
        while len(options) < 5 and attempts < 100:
            title = f"{random.choice(modifiers)} {random.choice(nouns)}"
            if title not in used_titles:
                options.append(title)
            attempts += 1

        if len(options) < 5:
            await member.send("Title generation failed. Please contact a mod.")
            return

        # Ask user to pick title
        dm = await member.create_dm()
        formatted = "\n".join([f"{i+1}. {t}" for i, t in enumerate(options)])
        await dm.send(
            f"Welcome to the Order of Iron and Ice, {member.name}.\n\n"
            f"Choose your title by replying with a number (1–5):\n{formatted}"
        )

        def check_choice(m): return m.author == member and m.content.isdigit() and 1 <= int(m.content) <= 5
        choice = await bot.wait_for('message', check=check_choice, timeout=60)
        title = options[int(choice.content) - 1]
        used_titles.add(title)
        save_used_title(title)


        # Ask for name
        await dm.send("What name would you like to be known as? (e.g., Thorne)")

        def check_name(m): return m.author == member and len(m.content.strip()) <= 32
        name_msg = await bot.wait_for('message', check=check_name, timeout=60)
        name = name_msg.content.strip()

        # Ask for title position
        await dm.send("Should your title come `before` or `after` your name?")
        def check_order(m): return m.author == member and m.content.lower() in ['before', 'after']
        order_msg = await bot.wait_for('message', check=check_order, timeout=60)
        position = order_msg.content.lower()

        final_title = f"{title} {name}" if position == "before" else f"{name}, {title}"
        try:
            print(f"Changing nickname for {member.name} to {final_title}")
            await member.edit(nick=final_title)
            print(f"Nickname successfully updated to {final_title}")
        except discord.Forbidden:
            print(f"Unable to change nickname for {member.name}. Bot may not have permissions.")
        except Exception as e:
            print(f"Error updating nickname: {e}")


        try:
            await dm.send(f"Your name is now **{final_title}**. Proceed to <#{redirect_channel.id}> to give your true name.")
        except discord.Forbidden:
            print(f"Unable to send DM to {member.name}. User might have DMs disabled.")


        # Log to #title-log
        log_msg = (
            f"🧊 **Title Assigned**\n"
            f"Member: {member.mention} ({member.name})\n"
            f"Title: `{title}`\n"
            f"Name: `{name}`\n"
            f"Final Nickname: `{final_title}`"
        )
        await channel_log.send(log_msg)

    except asyncio.TimeoutError:
        try:
            fallback_nick = f"Unrenowned {member.name}"
            await member.edit(nick=fallback_nick)
            await member.send(
                f"You took too long to respond, so you've been temporarily titled **{fallback_nick}**.\n"
                "Please contact a High Council member to begin the process again."
            )
            await channel_log.send(
                f"⚠️ **Unrenowned Assigned**\n"
                f"Member: {member.mention} ({member.name})\n"
                f"Reason: Timeout during title sequence."
            )
        except:
            pass


@bot.event
async def on_member_join(member):
    await bot.wait_until_ready()
    guild = member.guild
    log_channel = discord.utils.get(guild.text_channels, name="title-log")
    redirect_channel = discord.utils.get(guild.text_channels, name="hall-of-names")

    if log_channel and redirect_channel:
        await run_title_sequence(member, log_channel, redirect_channel)

# 🔁 Manual retitle command (mod-only)
@bot.command(name='retitle')
@commands.has_role('High Council')
async def retitle(ctx, member: discord.Member):
    log_channel = discord.utils.get(ctx.guild.text_channels, name="title-log")
    redirect_channel = discord.utils.get(ctx.guild.text_channels, name="hall-of-names")

    if log_channel and redirect_channel:
        await ctx.send(f"Retitling {member.mention}...")
        await run_title_sequence(member, log_channel, redirect_channel)

@retitle.error
async def retitle_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to use this command.")

bot.run("MTM1OTAyODEzMjY2MDY0MTkwMg.Guuddb.POByLfW_RDFoEyv6ZYG5RZow0USaLReMaGHtoI")
