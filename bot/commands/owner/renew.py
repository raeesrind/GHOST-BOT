# bot/cogs/code_converter.py

import os
import discord
from discord.ext import commands
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

class CodeConverter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        endpoint = "https://models.github.ai/inference"
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("⚠️ Missing GITHUB_TOKEN environment variable.")
        
        self.client = ChatCompletionsClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(token),
        )
        self.model = "openai/gpt-5"

        # SYSTEM PROMPT (persona)
        self.system_prompt = """
You are a code converter AI. Your job is to convert Discord bot command files 
written in discord.py into Eris (Node.js) modules with the same logic, same 
features, and same behavior.

Conversion rules:
- Use Eris (not discord.js).
- Always output as a Node.js command module:
  module.exports = {
    name: "commandname",
    description: "Description here",
    execute: async (bot, msg, args) => {
      // logic here
    }
  };
- Replace ctx.send() with bot.createMessage(msg.channel.id, ...).
- Replace ctx.author.display_name with msg.author.username.
- Rewrite embeds using Eris format:
  {
    embed: {
      title: "Title",
      description: "Description",
      color: 0x5865F2
    }
  }
- Preserve async/await as needed.
- Never hardcode prefix (assume handled by main bot).
- Output only the converted JavaScript code, no explanations or extra text.
"""

    @commands.command(name="convert")
    @commands.is_owner()  # ✅ Only bot owner can use this command
    async def convert(self, ctx: commands.Context):
        """
        Convert a discord.py command into Eris (Node.js) and return as .txt file.
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
            await ctx.trigger_typing()

            response = self.client.complete(
                messages=[
                    SystemMessage(self.system_prompt),
                    UserMessage(code),
                ],
                model=self.model
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
