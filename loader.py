import dash
import configparser
import data
import dash_bootstrap_components as dbc
import os
from html2dash import Html2Dash
import json_path
import web_requests

CONFIG = 'multipage_config.ini'
STYLES = [dbc.themes.LUX, './styles/app.css']
SCRIPTS = []

model = data
config = configparser.ConfigParser()
config.read(CONFIG)
page_name = None

if config.getboolean('app', 'UsePages'):
    try:
        os.mkdir('./pages')
    except FileExistsError:
        pass

    html2dash = Html2Dash(config, 'pages', True)
    for file in [f'./layouts/{x}' for x in os.listdir('./layouts') if x.endswith('.html')]:
        html2dash.convert(file, '/' if file.endswith(config['app']['MainPage']) else None)

    app = dash.Dash(__name__, use_pages=True, external_stylesheets=STYLES, external_scripts=SCRIPTS, meta_tags=[
        {
            "name": "viewport",
                "content": "width=device-width, initial-scale=1, maximum-scale=1",
        }
    ])
else:
    html2dash = Html2Dash(config, 'cache', False)
    page_name = html2dash.convert(f'./layouts/{config["app"]["MainPage"]}')
    app = dash.Dash(__name__, use_pages=False, external_stylesheets=STYLES, external_scripts=SCRIPTS)
