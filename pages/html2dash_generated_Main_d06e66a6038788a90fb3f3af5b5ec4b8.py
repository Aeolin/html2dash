import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output
from loader import model, config
import web_requests as req
import json_path as jp
from datetime import date, timedelta, time, datetime
import formatter as fmt
import io

dash.register_page(__name__, path='/')

layout = html.Div([
    html.H1("Home"),

    dcc.Link("Example Page",
        href="example"),

    html.Br(),

    dcc.Link("Data Demo",
        href="data_demo")])





