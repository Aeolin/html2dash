import dash
import configparser
import data
import dash_bootstrap_components as dbc
import os

CONFIG = 'multipage_config.ini'
STYLES = [dbc.themes.BOOTSTRAP, './styles/app.css']
SCRIPTS = []

model = data
config = configparser.ConfigParser()
config.read(CONFIG)
if config.getboolean('app', 'UsePages'):
    try:
        os.mkdir('./pages')
    except FileExistsError:
        pass

    app = dash.Dash(__name__, use_pages=True, external_stylesheets=STYLES, external_scripts=SCRIPTS)
else:
    app = dash.Dash(__name__, use_pages=False, external_stylesheets=STYLES, external_scripts=SCRIPTS)
