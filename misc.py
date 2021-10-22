import quart_discord
from quart import request, redirect, url_for, Blueprint, current_app
app = Blueprint('misc', __name__, template_folder='templates', static_folder='static')

@app.before_app_first_request
async def setup_discord():
    global discord
    discord = quart_discord.DiscordOAuth2Session(current_app)

@app.route('/license')
@app.route('/license.txt')
async def license():
    return await app.send_static_file("license.txt")

@app.route('/robots')
@app.route('/robots.txt')
async def robots():
    return await app.send_static_file("robots.txt")

@app.route('/sitemap')
@app.route('/sitemap.xml')
async def sitemap():
    return await app.send_static_file("sitemap.xml")

@app.route('/login')
async def oauth_login():
    try:
        callback_url = request.args['callback_url']
    except KeyError:
        callback_url = request.referrer if request.referrer is not None else url_for('homepage')
    return await discord.create_session(scope=['identify', 'email'], data={"callback_url": callback_url})

@app.route('/callback')
async def oauth_callback():
    try:
        data = await discord.callback()
    except quart_discord.exceptions.AccessDenied:
        return redirect(url_for('homepage'))
    try:
        return redirect(data['callback_url'])
    except KeyError:
        return redirect(url_for('homepage'))

@app.route('/logout')
async def oauth_logout():
    discord.revoke()
    return redirect(request.referrer if request.referrer is not None else url_for('homepage'))
