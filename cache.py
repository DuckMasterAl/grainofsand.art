avatar = "https://grainofsand.art/static/avatar.png"
border_color = ""
pronouns = {}
socials = {}
prices = {}

import asyncio, json, sys, aiohttp, tokens, os, config
async def recache(cache):# https://pgjones.gitlab.io/quart/how_to_guides/background_tasks.html
    while True:
        async with aiohttp.ClientSession() as session:# avatar and border
            async with session.get(f'https://discord.com/api/v9/users/{config.userid}', headers={"Authorization": f"Bot {tokens.bot_token}"}) as r:
                js = await r.json()
        cache.avatar = f"https://cdn.discordapp.com/embed/avatars/{int(js['discriminator']) % 5}.png" if js['avatar'] is None else f"https://cdn.discordapp.com/avatars/{js['id']}/{js['avatar']}"
        cache.border_color = js['banner_color']

        data = json.loads(open('grain/data.json' if sys.platform == 'linux' else 'data.json').read())# socials and pronouns
        cache.pronouns = data['pronouns']
        cache.socials = data['socials']
        cache.prices = data['prices']

        images = os.listdir('grain/static/gallery' if sys.platform == 'linux' else 'static/gallery')
        images.remove("raw")
        cache.images = images
        await asyncio.sleep(14400)
