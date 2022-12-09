from loader import app, config
import dash
from dash import dcc, html
import html2dash
import os

if config.getboolean('app', 'UsePages'):
    for file in [f'./layouts/{x}' for x in os.listdir('./layouts') if x.endswith('.html')]:
        name = html2dash.convert(file, 'pages', True, '/' if file.endswith(config['app']['MainPage']) else None)

    pages = dash.page_registry.items()
    app.layout = html.Div([dash.page_container])
else:
    file = './layouts/' + config['app']['MainPage']
    module_name = html2dash.convert(file, 'cache')
    page = __import__('cache.' + module_name)
    page = getattr(page, module_name)
    app.layout = page.make_layout()

if __name__ == '__main__':
    app.run_server(debug=config.getboolean('server', 'Debug'), port=config.getint('server', 'Port'), host=config['server']['Host'])