import dash
import configparser
import data
import dash_bootstrap_components as dbc
import os
import html2dash

CONFIG = 'multipage_config.ini'
STYLES = [dbc.themes.BOOTSTRAP, './styles/app.css']
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

    for file in [f'./layouts/{x}' for x in os.listdir('./layouts') if x.endswith('.html')]:
        html2dash.convert(file, 'pages', config, True, '/' if file.endswith(config['app']['MainPage']) else None)

    app = dash.Dash(__name__, use_pages=True, external_stylesheets=STYLES, external_scripts=SCRIPTS)
else:
    page_name = html2dash.convert(f'./layouts/{config["app"]["MainPage"]}', 'cache', config)
    app = dash.Dash(__name__, use_pages=False, external_stylesheets=STYLES, external_scripts=SCRIPTS)
