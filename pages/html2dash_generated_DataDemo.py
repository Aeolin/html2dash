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

dash.register_page(__name__, path='/data_demo')

layout = html.Div([
    html.H1("Earthquake Data",
        className="title"),

    html.Div([
        html.Div([
            html.Div([
                html.P("Date"),

                dcc.DatePickerSingle(id="DataDemo_date_range", 
                    date=date.today(), 
                    min_date_allowed=date(1970, 1, 1), 
                    max_date_allowed=date.today())],
                className="col-3"),

            html.Div([
                html.P("Select how many past days should be respected"),

                dcc.Slider(id="DataDemo_days", 
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
                dcc.Graph(id="DataDemo_scatter_quake_data")],
                className="col-6"),

            html.Div([
                dcc.Graph(id="DataDemo_geo_spatial_quakes")],
                className="col-6")],
            className="row")],
        className="container")])


def transform_generated_0fa76ba8627d4f8fa85e629e88fd9fb1(df):
    df = df[["time", "mag"]]
    df = df.dropna()
    return df

def transform_generated_d68f1de0ed3e4d459eedb75d3d58ae54(df):
    df = df[["time", "latitude", "longitude", "mag", "magType", "place", "depth"]]
    df = df.dropna()
    return df


@callback(
    Output(component_id="DataDemo_scatter_quake_data", component_property="figure"),
    Input(component_id="DataDemo_date_range", component_property="date"),
    Input(component_id="DataDemo_days", component_property="value"))
def update_DataDemo_scatter_quake_data(DataDemo_input_date, DataDemo_input_days):
    __output_DataDemo_scatter_quake_data_figure = px.scatter(
            transform_generated_0fa76ba8627d4f8fa85e629e88fd9fb1(
                pd.read_json(
                    jp.transform(
                        req.get(format="geojson", 
                            endtime=fmt.object(
                                date.fromisoformat(DataDemo_input_date), 
                            format="%Y-%m-%d"), 

                            starttime=fmt.object(
                                date.__sub__(
                                    date.fromisoformat(DataDemo_input_date), 

                                    timedelta(days=DataDemo_input_days)), 
                            format="%Y-%m-%d"), 
                        url="https://earthquake.usgs.gov/fdsnws/event/1/query"), 
                    json_path="$.features[*].properties"), 
                convert_dates=True)), 
        x="time", y="mag", title="Earthquake Data")
    return __output_DataDemo_scatter_quake_data_figure

@callback(
    Output(component_id="DataDemo_geo_spatial_quakes", component_property="figure"),
    Input(component_id="DataDemo_date_range", component_property="date"),
    Input(component_id="DataDemo_days", component_property="value"))
def update_DataDemo_geo_spatial_quakes(DataDemo_input_date, DataDemo_input_days):
    __output_DataDemo_geo_spatial_quakes_figure = px.scatter_geo(
            transform_generated_d68f1de0ed3e4d459eedb75d3d58ae54(
                pd.read_csv(
                    io.StringIO(
                        req.get(format="csv", 
                            endtime=fmt.object(
                                date.fromisoformat(DataDemo_input_date), 
                            format="%Y-%m-%d"), 

                            starttime=fmt.object(
                                date.__sub__(
                                    date.fromisoformat(DataDemo_input_date), 

                                    timedelta(days=DataDemo_input_days)), 
                            format="%Y-%m-%d"), 
                        url="https://earthquake.usgs.gov/fdsnws/event/1/query")), 
                sep=",")), 
        hover_data=["latitude", "longitude", "mag", "magType", "place", "depth", "time"], title="Earthquake Magnitudes", lat="latitude", lon="longitude")
    return __output_DataDemo_geo_spatial_quakes_figure