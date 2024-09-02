import asyncio
import discord
import sd
import json
import sqlite3 as sql
import ollama
import random

tokens = json.loads(open("token.json", "r").read())
naughty_words = json.loads(open("blocked_words.json", "r").read())

available_models = {
    "flux-dev": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
    "flux-schnell": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
    "boreal": "https://api-inference.huggingface.co/models/kudzueye/Boreal",
    "vintage-ads": "https://api-inference.huggingface.co/models/multimodalart/vintage-ads-flux",
    "flux-rl-lora": "https://api-inference.huggingface.co/models/XLabs-AI/flux-RealismLora",
    "hyper-sd": "https://api-inference.huggingface.co/models/ByteDance/Hyper-SD",
    "sdxl-turbo": "https://api-inference.huggingface.co/models/stabilityai/sdxl-turbo",
    "little-tinies": "https://api-inference.huggingface.co/models/alvdansen/littletinies",
    "enna-sketch-drawing": "https://api-inference.huggingface.co/models/alvdansen/enna-sketch-style",
    "flux-mona-lisa": "https://api-inference.huggingface.co/models/fofr/flux-mona-lisa",
    "half-illustration": "https://api-inference.huggingface.co/models/davisbro/half_illustration",
    "ps1-flux": "https://api-inference.huggingface.co/models/veryVANYA/ps1-style-flux",
    "softserve-anime": "https://api-inference.huggingface.co/models/alvdansen/softserve_anime",
    "lq-stable-diffusion-v1-4": "https://api-inference.huggingface.co/models/CompVis/stable-diffusion-v1-4"
}

active_process = []


class Process:
    def __init__(self, prompt="A cat holding up a sign that says \"Hello, world!\"",
                 channel: discord.TextChannel = None,
                 model: str = "flux-schnell",
                 author: discord.Member = None):
        self.prompt = prompt
        self.channel = channel
        self.model = model
        self.author = author

    async def run(self):
        if self.prompt == "_MAKE_":
            ai_response = ollama.chat(model="dolphin-mistral", messages=[
                {
                    "role": "system",
                    "content": "You shall only respond with what the user asked for, no surrounding text like \"Here's a prompt for you: \", because it's useless and NOT what the user asked for. ADDITIONALLY NO QUOTATION MARKS!"
                    # NOQA
                },
                {
                    "role": "system",
                    "content": f"You are using the {self.model} diffusion system, we are telling you because a model might be specialized in one thing and so you would have to lean towards its style (ex. anime, ps1 graphics), FOR EXAMPLE (example, which means that you could not be using that model) you are using a model called 'vintage-ads' (still an example), you would write something like 'Coke-a-cola advertisement with text saying \"quench your thirst\"'. DO NOT SPECIFY WHAT MODEL YOU ARE USING. Additionally, if your model sounds like a made up word, then it's probably just a standard image generator. YOU ARE USING {self.model} IMAGE GENERATOR, REMINDER THAT YOU ARE USING {self.model} IMAGE GENERATOR."
                },
                {
                    "role": "system",
                    "content": "Additionally, you should always start your prompt off with something like 'an image of' or 'a ps1 screenshot of' for clarity."
                },
                {
                    "role": "user",
                    "content": "Hi! Can you come up with a Stable Diffusion prompt for me? It cannot be NSFW/inappropriate but it can be creative. It cannot be too long as for the Diffusion model not get confused because of too many tokens. For example \"Cat holding up a sign saying Hello, world!\", but don't use that prompt or anything too similiar to it. YOU MUST ONLY RESPOND WITH THE PROMPT AND THE PROMPT ONLY, NOTHING ELSE AROUND IT. IMPORTANT: ONLY RESPOND WITH THE PROMPT, JUST THE PROMPT, PROMPT ONLY. ONLY GIVE THE PROMPT. DO NOT SURROUND YOUR RESPONSE WITH QUOTATION MARKS AND ESPECIALLY, ESPECIALLY DO NOT ADD ANY SURROUNDING TEXT LIKE \"Sure, here's a prompt for you\" OR \"How about: \" BECAUSE IT MESSES WITH THE AI"
                    # NOQA
                }
            ], options={"temperature": .8})
            self.prompt = ai_response['message']['content']  # TEMP
        notification = discord.Embed(
            title="Began Generation",
            description=f"Starting generating image with prompt:\n`{self.prompt}`",
            color=discord.Color.blurple()
        )
        notification.set_footer(text=self.model)
        notification.add_field(name="Prompter", value=self.author.name, inline=False)

        await self.channel.send(embed=notification)

        save_path = f"./storage/{self.author.id}.png"

        # Synchronous call - make sure sd.query is not blocking
        seed = random.randint(0, 1000000)
        status_code = sd.query(self.prompt, available_models[self.model], save_path, seed)
        if status_code:
            tell_failed = discord.Embed(
                title="Failed Generation",
                description=f"Failed Generation whilst generating \"{self.prompt}\"",
                color=discord.Color.red()
            )
            tell_failed.set_footer(text=f"Error occurred whilst using the model {self.model}")
            tell_failed.add_field(name="Status Code", value=str(status_code['status_code']))

            await self.channel.send(embed=tell_failed)
            return

        completed_notif = discord.Embed(
            title="Completed Generation",
            description=f"Completed generating image for <@{self.author.id}>",
            color=discord.Color.brand_green()
        )
        completed_notif.set_footer(text=self.model)
        completed_notif.add_field(name="Prompt", value=self.prompt, inline=False)
        completed_notif.add_field(name="Seed", value=str(seed), inline=False)

        file = discord.File(save_path, filename=f"{self.author}.png")
        completed_notif.set_image(url=f"attachment://{self.author}.png")

        await self.channel.send(embed=completed_notif, file=file)


class BotClient(discord.Client):
    def __init__(self, intents):
        super().__init__(intents=intents)

    def load_database(self):
        db = sql.connect("database.db")
        cursor = db.cursor()
        return cursor, db

    async def on_ready(self):
        print(f'Bot is ready.\n{"-" * 50}')
        await self.loop.create_task(self.loop_tasks())

    async def on_message(self, message):
        global active_process
        author = message.author
        content = message.content

        if author.bot:
            return

        if len(content) > 2 and content[0] == ".":
            content = content[1:]
            splitup = content.split(" ")
            if splitup[0] == "gen":
                state_instructions = True
                try:
                    model = splitup[1]
                    if model in available_models:
                        state_instructions = False

                        for word in splitup:
                            if word.lower() in naughty_words:
                                await message.channel.send(
                                    "# Blocked Prompt\nWe have decided to block your prompt as we believe it can generate potentially harmful or NSFW content.")
                                return
                        prompt = " ".join(splitup[2:])
                        active_process.append(Process(
                            prompt=prompt,
                            author=message.author,
                            channel=message.channel,
                            model=model,
                        ))
                        print("Added to processes")
                    else:
                        state_instructions = False
                        response = '# Invalid Model\nTry one of these models:'
                        for count, model in enumerate(available_models.keys()):
                            response += f'\n{count}. `{model}`'
                        response += "\nYou must explicitly say the name of the model, not just the number."
                        await message.channel.send(response)
                except Exception as e:
                    state_instructions = True
                    print(e)
                if state_instructions:
                    await message.channel.send("""# Guide
You made a mistake when typing in your commands, here's how to use Artivelle
You can start generating something by running `.gen <MODEL> <PROMPT>`
You can view all the models by typing in `.models`
That's about all there is to it.""")

            elif splitup[0] == "models":
                response = '# Models\nHere are all the models we offer:'
                for count, model in enumerate(available_models.keys()):
                    response += f'\n{count}. `{model}`'
                response += "\nYou must explicitly say the name of the model, not just the number."
                await message.channel.send(response)
            elif splitup[0] == "surprise-me":
                model = random.choice(list(available_models.keys()))

                active_process.append(Process(
                    prompt="_MAKE_",
                    author=message.author,
                    channel=message.channel,
                    model=model,
                ))
                print("Added to processes")

    async def loop_tasks(self):
        global active_process
        while True:
            if active_process:
                print("Started distilling image")
                first_priority = active_process.pop(0)
                await first_priority.run()
            await asyncio.sleep(1)


bot_intents = discord.Intents.default()
bot_intents.message_content = True

client = BotClient(intents=bot_intents)
client.run(tokens['token'])
