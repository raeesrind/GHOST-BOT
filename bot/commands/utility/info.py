import discord
from discord.ext import commands
import os
import time

start_time = time.time()

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="info", help="Get detailed bot information.")
    async def info(self, ctx):
        uptime_seconds = int(time.time() - start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

        client_id = os.getenv("BOT_CLIENT_ID", "YOUR_CLIENT_ID")

        embed = discord.Embed(
            title="GHOST Bot Information",
            description="Your powerful multipurpose moderation and utility bot. :GhostSuccess:",
            color=discord.Color.blurple()
        )

        embed.add_field(name="Version", value="1.0.0", inline=True)
        embed.add_field(name="Library", value="`discord.py`", inline=True)
        embed.add_field(name="Creator", value="`_gh00ost_`", inline=True)
        embed.add_field(name="Servers", value=f"`{len(self.bot.guilds):,}`", inline=True)
        embed.add_field(
            name="Users",
            value=f"`{sum(g.member_count or 0 for g in self.bot.guilds):,}`",
            inline=True
        )
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(
            name="Get Premium",
            value=":construction: **Coming Soon**",
            inline=True
        )

        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)

        embed.set_footer(text=f"Shard: {ctx.guild.shard_id if ctx.guild.shard_id else 0} • :GhostSuccess:")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="➕ Invite GHOST", url=f"https://discord.com/oauth2/authorize?client_id={client_id}&scope=bot+applications.commands&permissions=8"))
        

        await ctx.send(embed=embed, view=view)

    @commands.command(name="help", help="List all bot commands or get info about a specific command.")
    async def help(self, ctx, *, command_name: str = None):
        if command_name:
            cmd = self.bot.get_command(command_name)
            if cmd:
                desc = cmd.help or (cmd.callback.__doc__ or "No description provided.").strip()
                embed = discord.Embed(
                    title=f"📘 Help: {cmd.name}",
                    description=desc,
                    color=discord.Color.green()
                )
                embed.add_field(name="Usage", value=f"?{cmd.name} {cmd.signature or ''}".strip(), inline=False)
                embed.set_footer(text="<> = required, [] = optional")
                return await ctx.send(embed=embed)
            return await ctx.send(":GhostError: No command found with name `{command_name}`.")

        embed = discord.Embed(
            title=f"Server: {ctx.guild.name}",
            description="Commands in this server start with `?`\n\n**Help & Support**\n[Guides](https://drive.google.com)\n[Commands List](https://raeesrind.github.io/docs.GHOST/)\n[GHOST Status](https://yourbotstatuspage.com)\n\n**Get GHOST**\n[Add GHOST to your Server](https://discord.com/oauth2/authorize?client_id={os.getenv('BOT_CLIENT_ID', 'YOUR_CLIENT_ID')}&scope=bot+applications.commands&permissions=8)\n[Get Premium](https://ghost.premium.com) *(Coming Soon)*",
            color=discord.Color.blue()
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="➕ Invite GHOST", url=f"https://discord.com/oauth2/authorize?client_id={os.getenv('BOT_CLIENT_ID', 'YOUR_CLIENT_ID')}&scope=bot+applications.commands&permissions=8"))
        view.add_item(discord.ui.Button(label="📊 GHOST Status", url="https://yourbotstatuspage.com"))

        try:
            await ctx.author.send(embed=embed, view=view)
        except discord.Forbidden:
            await ctx.send(embed=embed, view=view)

    @commands.command(name="premium", help="Get information about GHOST Premium.")
    async def premium(self, ctx):
        embed = discord.Embed(
            title="GHOST Premium",
            description=(
                ":GhostSuccess: Premium is not available yet.\n\n"
                "🚧 We are actively working on Premium features.\n"
                "Stay tuned for priority support, custom automod, extended logs, dashboard access, and more!"
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text="Coming Soon • GHOST")

        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(embed=embed)

    @commands.command(name="uptime", help="Check the bot's uptime.")
    async def uptime(self, ctx):
        uptime_seconds = int(time.time() - start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

        embed = discord.Embed(
            title="GHOST Uptime",
            description=f"**Uptime**: {uptime}\n**PID**: 1 | GHOST Core | Cluster 001 | Shard {ctx.guild.shard_id if ctx.guild.shard_id else 0}",
            color=discord.Color.green()
        )
        embed.set_footer(text="Last restarted recently")
        await ctx.send(embed=embed)

    @commands.command(name="stats", help="View GHOST bot stats.")
    async def stats(self, ctx):
        uptime_seconds = int(time.time() - start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

        embed = discord.Embed(
            title="GHOST Bot Stats",
            description=":GhostSuccess: Current performance overview:",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Guilds", value=f"`{len(self.bot.guilds):,}`", inline=True)
        embed.add_field(
            name="Users",
            value=f"`{sum(g.member_count or 0 for g in self.bot.guilds):,}`",
            inline=True
        )
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.add_field(name="Events/sec", value="~1,024/sec", inline=True)
        embed.add_field(name="Free Mem", value="~1.2 GB / 4 GB", inline=True)
        embed.add_field(name="PID", value="1 | GHOST Core | Cluster 001", inline=True)

        embed.set_footer(text="Updated just now • GHOST")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Info(bot))
