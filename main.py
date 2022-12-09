from loader import app, config, page_name
import dash
from dash import html

if config.getboolean('app', 'UsePages'):
    app.layout = html.Div([dash.page_container])
else:
    page = __import__('cache.' + page_name)
    page = getattr(page, page_name)
    app.layout = page.make_layout()

if __name__ == '__main__':
    app.run_server(debug=config.getboolean('server', 'Debug'), port=config.getint('server', 'Port'), host=config['server']['Host'])