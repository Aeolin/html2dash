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

dash.register_page(__name__, path='/data_demo')

layout = html.Div([
    html.H1("Earthquake Data",
        className="title"),

    html.Div([
        html.Div([
            html.Div([
                html.P("Date"),

                dcc.DatePickerSingle(id="date_range", 
                    date=date.today(), 
                    min_date_allowed=date(1970, 1, 1), 
                    max_date_allowed=date.today())],
                className="col-3"),

            html.Div([
                html.P("Select how many past days should be respected"),

                dcc.Slider(id="days", 
                    min=1, 
                    max=30, 
                    step=1, 
                    value=3, 
                    marks=None,
                    tooltip={"placement": "bottom","always_visible": True})],
                className="col-9")],
            className="row")],
        className="container"),

    html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id="scatter_quake_data")],
                className="col-6"),

            html.Div([
                dcc.Graph(id="geo_spatial_quakes")],
                className="col-6")],
            className="row")],
        className="container")])


def transform_generated_1bdfef1632c44920bf404fb8630f9962(df):
    df = df[["time", "mag"]]
    df = df.dropna()
    return df

def transform_generated_bad9706967d147a6a9271e4936ec43d6(df):
    df = df[["time", "latitude", "latitude", "longitude", "mag", "magType", "place", "depth"]]
    df = df.dropna()
    return df


@callback(
    Output(component_id="scatter_quake_data", component_property="figure"),
    Output(component_id="geo_spatial_quakes", component_property="figure"),
    Input(component_id="date_range", component_property="date"),
    Input(component_id="days", component_property="value"))
def update(input_date, input_days):
    __output_scatter_quake_data_figure = px.scatter(
            transform_generated_1bdfef1632c44920bf404fb8630f9962(
                pd.read_json(
                    jp.transform(
                        req.get(format="geojson", 
                            endtime=fmt.object(
                                date.fromisoformat(input_date), 
                            format="%Y-%m-%d"), 

                            starttime=fmt.object(
                                date.__sub__(
                                    date.fromisoformat(input_date), 

                                    timedelta(days=input_days)), 
                            format="%Y-%m-%d"), 
                        url="https://earthquake.usgs.gov/fdsnws/event/1/query"), 
                    json_path="$.features[*].properties"), 
                convert_dates=True)), 
        x="time", y="mag", title="Earthquake Data")
    __output_geo_spatial_quakes_figure = px.scatter_geo(
            transform_generated_bad9706967d147a6a9271e4936ec43d6(
                pd.read_csv(
                    io.StringIO(
                        req.get(format="csv", 
                            endtime=fmt.object(
                                date.fromisoformat(input_date), 
                            format="%Y-%m-%d"), 

                            starttime=fmt.object(
                                date.__sub__(
                                    date.fromisoformat(input_date), 

                                    timedelta(days=input_days)), 
                            format="%Y-%m-%d"), 
                        url="https://earthquake.usgs.gov/fdsnws/event/1/query")), 
                sep=",")), 
        hover_data=["latitude", "longitude", "mag", "magType", "place", "depth", "time"], title="Earthquake Magnitudes", lat="latitude", lon="longitude")
    return __output_scatter_quake_data_figure, __output_geo_spatial_quakes_figure