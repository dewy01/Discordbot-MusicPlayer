import discord
import asyncio
from discord.ext import commands
import youtube_dl

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

queues = {}

ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')


async def stop_playing(guild):
    voice = discord.utils.get(bot.voice_clients, guild=guild)
    if voice and voice.is_playing():
        voice.stop()
        queues[guild.id] = []
        await voice.disconnect()


@bot.command()
async def play(ctx, *, url):
    guild_id = ctx.guild.id

    if not ctx.author.voice:
        await ctx.send("You're not connected to a voice channel.")
        return

    channel = ctx.author.voice.channel
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    if guild_id not in queues:
        queues[guild_id] = []

    queues[guild_id].append(url)

    if not voice.is_playing():
        await play_next_song(ctx, guild_id)


async def play_next_song(ctx, guild_id):
    if guild_id in queues and queues[guild_id]:
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_connected():
            try:
                url = queues[guild_id].pop(0)
                info = await asyncio.to_thread(ytdl.extract_info, url, download=False)
                URL = info['formats'][0]['url']
                voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS),
                           after=lambda e: bot.loop.create_task(play_next_song(ctx, guild_id)))
                voice.is_playing()
            except Exception as e:
                print(f"An error occurred while playing the next song: {e}")
                await play_next_song(ctx, guild_id)
    else:
        # Kolejka jest pusta, wysyłamy wiadomość o braku piosenek
        await ctx.send("The song queue is empty. Add songs with the !play command.")


@bot.command()
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_playing():
        voice.stop()
        await ctx.send("Song skipped.")


@bot.command()
async def stop(ctx):
    await stop_playing(ctx.guild)
    await ctx.send("Player stopped and queue cleared.")


@bot.command()
async def leave(ctx):
    await stop_playing(ctx.guild)
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I am not connected to any voice channel.")

# Uruchomienie bota
bot.run('TOKEN')
