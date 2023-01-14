import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, callback
from dash.dependencies import Input, Output, State
from loader import model, config
import web_requests as req
import json_path as jp
from datetime import date, timedelta, time, datetime
import formatter as fmt
import io

dash.register_page(__name__, path='{page}')

layout = {layout}


{methods}


{update}