"""
Discord Bot Interface for AI Development Pipeline
Provides user interaction through Discord
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from agents.master_agent import MasterAgent
from dotenv import load_dotenv

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Initialize Master Agent
master = MasterAgent()


@bot.event
async def on_ready():
    """Called when bot is ready"""
    print(f'🤖 AI Development Pipeline Bot is ready!')
    print(f'👤 Logged in as: {bot.user.name} (ID: {bot.user.id})')
    print(f'🔗 Connected to {len(bot.guilds)} server(s)')
    print('─' * 50)

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for project requests | !help"
        )
    )


@bot.event
async def on_message(message):
    """Handle all messages"""
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if isinstance(message.channel, discord.DMChannel) or bot.user in message.mentions:
        async with message.channel.typing():
            content = message.content.replace(f'<@{bot.user.id}>', '').strip()
            response = await master.process_user_message(
                content, str(message.author.id)
            )
            if len(response) > 2000:
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                for chunk in chunks:
                    await message.channel.send(chunk)
            else:
                await message.channel.send(response)


@bot.command(name='new', aliases=['create', 'start'])
async def new_project(ctx, *, description: str):
    """
    Start a new project
    Usage: !new <project description>
    Example: !new Create a task management app with React and FastAPI
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_new_project(description, str(ctx.author.id))
        await ctx.send(response)


@bot.command(name='status', aliases=['info', 'progress'])
async def project_status(ctx):
    """
    Check current project status
    Usage: !status
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_status_check()
        await ctx.send(response)


@bot.command(name='task', aliases=['implement', 'code'])
async def code_task(ctx, *, task_description: str):
    """
    Implement a specific task or feature
    Usage: !task <task description>
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_code_task(task_description, str(ctx.author.id))
        await ctx.send(response)


@bot.command(name='deploy', aliases=['ship', 'release'])
async def deploy_project(ctx, action: str = ""):
    """
    Deploy the active project via Docker + Cloudflare Tunnel.
    Shows existing URL if already deployed.
    Usage: !deploy [redeploy]
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_deploy_project(action, str(ctx.author.id))
        await _send_chunked(ctx, response)


@bot.command(name='run', aliases=['pipeline'])
async def run_pipeline(ctx, *, action: str = "pipeline"):
    """
    Run the full automated pipeline
    Usage: !run pipeline
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_run_full_pipeline(action, str(ctx.author.id))
        await _send_chunked(ctx, response)


@bot.command(name='workers')
async def workers_command(ctx, action: str = "status"):
    """
    Manage worker agents
    Usage: !workers [start|stop|status]
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        action = action.lower()
        if action == "start":
            response = await master.start_workers()
        elif action == "stop":
            response = await master.stop_workers()
        else:
            response = await master.worker_status()
        await _send_chunked(ctx, response)


@bot.command(name='monitor')
async def monitor_command(ctx, action: str = "status"):
    """
    Manage the CI/CD pipeline monitor
    Usage: !monitor [start|stop|status]
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_monitor_status(action)
        await _send_chunked(ctx, response)


@bot.command(name='projects', aliases=['list'])
async def projects_command(ctx):
    """
    List all projects with status and deploy URLs
    Usage: !projects
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_projects_list()
        await _send_chunked(ctx, response)


@bot.command(name='switch')
async def switch_command(ctx, name: str):
    """
    Switch to a different project by name
    Usage: !switch <project_name>
    Example: !switch project_20260219_165036
    """
    master.set_notify_channel(ctx.channel)
    async with ctx.typing():
        response = await master.handle_switch_project(name)
        await _send_chunked(ctx, response)


@bot.command(name='help')
async def help_command(ctx):
    """Show help message"""
    embed = discord.Embed(
        title="🤖 AI Development Pipeline Bot",
        description=(
            "I'm your autonomous development assistant! "
            "I can build entire projects from just a description."
        ),
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🚀 Start a New Project",
        value="`!new <description>` — Start a new project\n"
              "Example: `!new Build a blog with React and Django`",
        inline=False
    )
    embed.add_field(
        name="📂 Multi-Project Management",
        value=(
            "`!projects` — List all projects with status and deploy URLs\n"
            "`!switch <name>` — Switch the active project"
        ),
        inline=False
    )
    embed.add_field(
        name="📊 Check Status",
        value="`!status` — Get current project status and progress",
        inline=False
    )
    embed.add_field(
        name="💻 Implement a Task",
        value="`!task <description>` — Implement a specific feature\n"
              "Example: `!task Add user login with Google OAuth`",
        inline=False
    )
    embed.add_field(
        name="🌐 Deploy",
        value=(
            "`!deploy` — Deploy via Docker + Cloudflare Tunnel → public URL\n"
            "`!deploy redeploy` — Rebuild and redeploy"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Worker Agents",
        value=(
            "`!workers start` — Start background worker agents\n"
            "`!workers stop` — Stop worker agents\n"
            "`!workers status` — Check queue sizes and worker states"
        ),
        inline=False
    )
    embed.add_field(
        name="🔍 Pipeline Monitor",
        value=(
            "`!monitor start` — Start CI/CD monitoring\n"
            "`!monitor stop` — Stop the monitor\n"
            "`!monitor status` — Show monitor state and fix attempt history"
        ),
        inline=False
    )
    embed.add_field(
        name="💬 Chat with Me",
        value="DM me or mention me to have a conversation!",
        inline=False
    )

    embed.set_footer(text="Powered by Claude Code CLI + Multi-Agent System")
    await ctx.send(embed=embed)


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Use `!help` to see command usage.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `!help` to see available commands.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")
        print(f"Error: {error}")


# ==========================================
# HELPERS
# ==========================================


async def _send_chunked(ctx, response: str):
    """Send a potentially long response in 2000-char chunks."""
    if len(response) > 2000:
        chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
        for chunk in chunks:
            await ctx.send(chunk)
    else:
        await ctx.send(response)


def run_bot():
    """Run the Discord bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables")
        return

    try:
        bot.run(token)
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")


if __name__ == "__main__":
    run_bot()
