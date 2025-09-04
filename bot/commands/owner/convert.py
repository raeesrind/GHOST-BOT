# bot/cogs/code_converter.py

import os
import discord
from discord.ext import commands
from openai import OpenAI

class CodeConverter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # GitHub Models endpoint + token
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("⚠️ Missing GITHUB_TOKEN environment variable.")
        
        endpoint = "https://models.github.ai/inference"
        self.client = OpenAI(
            base_url=endpoint,
            api_key=token,
        )
        self.model = "openai/gpt-4o"   # ✅ using gpt-4o (available)

        # System prompt for consistent conversion
        self.system_prompt = """ 
You are a code converter AI. Your job is to convert Discord bot command files 
written in discord.py into Discord.js v14.22.1 (Node.js) modules with the same logic, 
features, and behavior.

Conversion rules:
- Use Discord.js v14.22.1 (not Eris).
- Always output as a Node.js module:

module.exports = {
  name: "commandname",
  description: "Description here",
  execute: async (client, message, args) => {
    // logic here
  }
};

Events:
- @bot.event async def on_ready() → client.once("ready", () => { ... });
- @bot.event async def on_message(msg) → client.on("messageCreate", async (msg) => { ... });
- @bot.event async def on_command_error(ctx, error) → handled inside messageCreate with try/catch and message.channel.send embeds.

General replacements:
- ctx.send(...) → message.channel.send(...).
- ctx.author.display_name → message.member?.displayName || message.author.username.
- ctx.author.mention → `<@${message.author.id}>`.
- ctx.message.attachments[0].url → message.attachments.first()?.url.
- ctx.guild.name → message.guild?.name.
- ctx.guild.id → message.guild?.id.
- ctx.channel.name → message.channel.name.
- ctx.channel.id → message.channel.id.
- ctx.message.id → message.id.
- ctx.message.created_at → message.createdTimestamp.
- ctx.me → message.guild?.members.cache.get(client.user.id).
- Member mention: `<@${user.id}>`.
- Role mention: `<@&${role.id}>`.
- Channel mention: `<#${channel.id}>`.
- Permissions: member.permissions.has("KickMembers") etc.

Arguments:
- Python `*args` (capture full string) → args.join(" ").
- args[0], args[1] etc. → args[0], args[1].
- Convert int(args[0]) → parseInt(args[0]).

Embeds:
- Use Discord.js EmbedBuilder format:
  const embed = new EmbedBuilder()
    .setTitle("Title")
    .setDescription("Description")
    .setColor(0x5865F2)
    .addFields({ name: "Field1", value: "Some text", inline: true })
    .setFooter({ text: "Footer text" })
    .setTimestamp();

Extras:
- ctx.message.add_reaction("👍") → message.react("👍").
- ctx.message.remove_reaction(...) → message.reactions.cache.get("👍")?.users.remove(userId).
- ctx.message.clear_reactions() → message.reactions.removeAll().
- ctx.typing() → message.channel.sendTyping().
- await asyncio.sleep(n) → await new Promise(r => setTimeout(r, n * 1000));
- datetime.utcnow() → new Date().
- timedelta(seconds=n) → n * 1000 ms with setTimeout.
- ctx.author.avatar.url → message.author.displayAvatarURL().
- user.display_name → user.displayName || user.username.

Database (aiosqlite → Node.js better-sqlite3):
- import Database from "better-sqlite3";
- const db = new Database("file.db");
- async with aiosqlite.connect("file.db") as db → const db = new Database("file.db");
- await db.execute("SQL", params) → db.prepare("SQL").run(params);
- await db.execute_fetchall("SQL", params) → const rows = db.prepare("SQL").all(params);
- await db.execute_fetchone("SQL", params) → const row = db.prepare("SQL").get(params);
- await db.commit() → not needed (better-sqlite3 is synchronous and auto-commits).

Database (firebase_admin → Firebase JS SDK):
- from firebase_admin import firestore → const { getFirestore } = require("firebase-admin/firestore");
- db = firestore.client() → const db = getFirestore();
- db.collection("users").document(uid).get() →
    const doc = await db.collection("users").doc(uid).get();
- doc.to_dict() → doc.data();
- db.collection("users").document(uid).set({...}) → await db.collection("users").doc(uid).set({...});
- db.collection("users").document(uid).update({...}) → await db.collection("users").doc(uid).update({...});
- db.collection("users").document(uid).delete() → await db.collection("users").doc(uid).delete();

Environment variables:
- from dotenv import load_dotenv → require("dotenv").config({ path: path.resolve(__dirname, "../../config/.env") });

Intents (discord.py → Discord.js):
- discord.Intents.all() →
    const { GatewayIntentBits, Partials, Client } = require("discord.js");
    const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });

Rules:
- Always use async/await for bot actions and database calls.
- Use backtick template literals for variables and multiline text.
- Never hardcode prefixes (assume main bot handles it).
- Output ONLY the converted JavaScript code, nothing else.
- Always include at the top of the file (if used):
    const { Client, GatewayIntentBits, EmbedBuilder } = require("discord.js");
    const Database = require("better-sqlite3");
"""

    @commands.command(name="convert")
    async def convert(self, ctx: commands.Context):
        """
        Convert a discord.py command into Discord.js and return as .txt file.
        Usage:
          - ?convert <attach .py or .txt file>
          - ?convert <paste raw code>
        """
        # Case 1: If user attaches a file
        if ctx.message.attachments:
            file = ctx.message.attachments[0]
            code = await file.read()
            code = code.decode("utf-8")
        else:
            # Case 2: If user just writes raw code
            code = ctx.message.content[len(ctx.prefix + ctx.invoked_with):].strip()

        if not code:
            await ctx.send("⚠️ Please provide a `.py`/`.txt` file or raw Python code.")
            return

        try:
            async with ctx.typing():
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": code},
                    ],
                )

            converted_code = response.choices[0].message.content.strip()

            # Save to .txt file
            output_filename = "converted_command.txt"
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(converted_code)

            # Send file back
            await ctx.send(
                content="✅ Converted successfully!",
                file=discord.File(output_filename)
            )

        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")


async def setup(bot: commands.Bot):
    await bot.add_cog(CodeConverter(bot))
