import os, sys, tokens, quart_discord, cache, asyncio, json, aiohttp, config, os, base64, io, aiofiles
from quart import Quart, render_template, redirect, request, url_for, current_app, jsonify, session
from misc import app as misc_app
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from PIL import Image

app = Quart(__name__)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app.config["DISCORD_CLIENT_ID"] = "757949379792601088"
app.config["DISCORD_CLIENT_SECRET"] = tokens.client_secret
app.config["DISCORD_BOT_TOKEN"] = tokens.bot_token
app.config["DISCORD_REDIRECT_URI"] = "https://grainofsand.art/callback" if sys.platform =='linux' else "http://localhost:8500/callback"
app.secret_key = tokens.secret_key
discord = quart_discord.DiscordOAuth2Session(app)
app.url_map.strict_slashes = False
app.register_blueprint(misc_app)

@app.before_request
async def path_redirects():
    path = request.path.lower()# case insensitive for requests
    if path != '/' and path.endswith('/'):# trailing slash
        path = path[:-1]
    if path.endswith('.html'):# removes .html from requests
        path = path[:-5]
    if path == '/index':# /index -> /
        path = '/'
    if path != request.path:# redirect if something has changed
        return redirect(path)

if sys.platform != 'linux':# Add no cache headers if running locally
    async def cache_headers(r):
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        return r
    app.after_request(cache_headers)

@app.before_serving
async def schedule_cache():
    asyncio.ensure_future(cache.recache(cache))

@app.route('/')
async def homepage():
    return await render_template("index.html", avatar=cache.avatar, accent_color=cache.border_color, pronouns=cache.pronouns, socials=cache.socials, gallery=cache.images)

@app.route('/commission')
@app.route('/prices')
async def commission_info():
    try:
        user = await discord.fetch_user()
        user_data = {"username": f"{user.username}#{user.discriminator}", "avatar": user.avatar_url[:-4], "id": user.id, "email": user.email}
    except quart_discord.exceptions.Unauthorized:
        user_data = None
    return await render_template("commission.html", avatar=cache.avatar, accent_color=cache.border_color, pronouns=cache.pronouns, socials=cache.socials, discord=user_data, prices=cache.prices)

@app.route('/api/submit-commission', methods=["POST"])
@quart_discord.requires_authorization
async def submit_commission():
    try:
        form_list = await request.data
        description = eval(form_list.decode("utf-8"))['description']
    except:
        return jsonify({"error": True, "message": "No description was provided."}), 400

    user = await discord.fetch_user()
    async with aiohttp.ClientSession() as session:
        async with session.put(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{user.id}/roles/{config.commissioned_role_id}', headers={"Authorization": f"Bot {tokens.bot_token}", "X-Audit-Log-Reason": f"Request made through Web Form", "content-type": "application/json"}) as r:
            if r.status != 204:
                return jsonify({"error": True, "message": "User not in discord."}), 401

        async with session.post(f'https://discord.com/api/v9/guilds/{config.guild_id}/channels', headers={"Authorization": f"Bot {tokens.bot_token}", "X-Audit-Log-Reason": f"Request made through Web Form", "content-type": "application/json"},
        data=json.dumps({"name": f"art-{user.name}", "type": 0, "position": 0, "parent_id": str(config.category_id), "topic": f"Email: {user.email}",
        "permission_overwrites": [{"id": str(user.id), "type": 1, "allow": "3072"}, {"id": str(config.guild_id), "type": 0, "deny": "1024"}, {"id": str(config.admin_role_id), "type": 0, "allow": "1024"}]})) as r:
            channel = await r.json()
            print(channel)

        async with session.post(f'https://discord.com/api/v9/channels/{channel["id"]}/messages', headers={"Authorization": f"Bot {tokens.bot_token}", "content-type": "application/json"},
        data=json.dumps({"content": f"<@{user.id}> <@&{config.admin_role_id}>", "embeds": [{"color": 3447003, "author": {"name": f"New Commission from {user.name}", "icon_url": str(user.avatar_url)}, "description": str(description)}]})) as r:
            message = await r.json()
            print(message)

        async with session.put(f'https://discord.com/api/v9/channels/{channel["id"]}/pins/{message["id"]}', headers={"Authorization": f"Bot {tokens.bot_token}", "content-type": "application/json"}) as r:
            pass

    return jsonify({"error": False, "message": "Commission ticket created successfully."}), 200

@app.route('/admin')
@quart_discord.requires_authorization
async def admin():
    user = await discord.fetch_user()
    if user.id not in [443217277580738571, config.userid]:
        return redirect(url_for('homepage'))
    return await render_template("admin.html", avatar=cache.avatar, accent_color=cache.border_color, pronouns=cache.pronouns, socials=cache.socials, prices=cache.prices, gallery=cache.images)

@app.route('/api/admin-form', methods=["POST"])
@quart_discord.requires_authorization
async def admin_form():
    user = await discord.fetch_user()
    if user.id not in [443217277580738571, config.userid]:
        return redirect(url_for('homepage'))
    data = (await request.form).to_dict()
    new_images = (await request.files).to_dict(flat=False)
    print(new_images)
    data_to_dump = {"pronouns": {"name": data['pronoun-name'], "color": data['pronoun-color'], "link": data['pronoun-link']},
                    "socials": {"discord": data['socials-discord'], "twitter": data['socials-twitter'], "twitch": data['socials-twitch'], "youtube": data['socials-youtube']},
                    "prices": {"sticker": data['prices-sticker'], "pfp": data['prices-pfp'], "banner": data['prices-banner'], "ref": data['prices-ref'], "animation": data['prices-animation']}}
    with open('grain/data.json' if sys.platform == 'linux' else 'data.json', 'w') as f:
        json.dump(data_to_dump, f, indent=2)

    cache.pronouns = data_to_dump['pronouns']
    cache.socials = data_to_dump['socials']
    cache.prices = data_to_dump['prices']
    if new_images['image'][0].filename != '':
        async with aiohttp.ClientSession() as session:
            for x in new_images['image']:
                filename = (x.filename.lower()).replace(' ', '_')
                raw_img_bytes = x.read()
                raw_file = await aiofiles.open(f'grain/static/gallery/raw/{filename}' if sys.platform == 'linux' else f'static/gallery/raw/{filename}', mode='wb')
                await raw_file.write(raw_img_bytes)
                await raw_file.close()

                img = Image.open(io.BytesIO(raw_img_bytes))
                basewidth = 300# thanks stackoverflow!
                wpercent = (basewidth/float(img.size[0]))
                hsize = int((float(img.size[1])*float(wpercent)))
                img = img.resize((basewidth,hsize), Image.HAMMING)

                img_bytes = io.BytesIO()
                img.save(img_bytes, optimize=True, quality=85, format='PNG')
                async with session.post('https://api.tinify.com/shrink', headers={"Authorization": "Basic " + (base64.b64encode(f"{tokens.tinypng}".encode())).decode()}, data=img_bytes.getvalue()) as r:
                    js = await r.json()

                async with session.get(js['output']['url']) as resp:
                    f = await aiofiles.open(f'grain/static/gallery/{filename}' if sys.platform == 'linux' else f'static/gallery/{filename}', mode='wb')
                    await f.write(await resp.read())
                    await f.close()
        images_to_cache = os.listdir('grain/static/gallery' if sys.platform == 'linux' else 'static/gallery')
        images_to_cache.remove("raw")
        cache.images = images_to_cache

    return await render_template("admin_form.html")

@app.route('/api/admin-image', methods=["DELETE"])
@quart_discord.requires_authorization
async def admin_delete_image():
    user = await discord.fetch_user()
    if user.id not in [443217277580738571, config.userid]:
        return redirect(url_for('homepage'))
    try:
        form_list = await request.data
        filename = eval(form_list.decode("utf-8"))['image']
    except:
        return jsonify({"error": True, "message": "No image was provided."}), 400

    path = f'grain/static/gallery/{filename}' if sys.platform == 'linux' else f'static/gallery/{filename}'
    raw_path = f'grain/static/gallery/raw/{filename}' if sys.platform == 'linux' else f'static/gallery/raw/{filename}'
    if os.path.exists(path):
        os.remove(path)
        try:
            os.remove(raw_path)
        except FileNotFoundError:
            pass
        images_to_cache = os.listdir('grain/static/gallery' if sys.platform == 'linux' else 'static/gallery')
        images_to_cache.remove("raw")
        cache.images = images_to_cache
        return jsonify({"error": False, "message": "Deleted image successfully."}), 200
    else:
        return jsonify({"error": False, "message": "Invalid image provided."}), 404

@app.route('/discord')
async def discord_server():
    return redirect(cache.socials['discord'])

@app.errorhandler(quart_discord.exceptions.Unauthorized)
async def handle_unauthorized(e):
    return redirect(url_for('misc.oauth_login', callback_url=str(request.url)))

@app.errorhandler(InvalidGrantError)
async def handle_discord_oauth_bug(e):
    discord.revoke()
    return redirect(request.referrer if request.referrer is not None else url_for('homepage'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8500, debug=True)
