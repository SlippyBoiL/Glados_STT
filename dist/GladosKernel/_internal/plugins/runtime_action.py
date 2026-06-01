import subprocess

def discord_message(channel, message):
    subprocess.run([sys.executable, 'plugins/skill_discord.py', channel, message], check=True)