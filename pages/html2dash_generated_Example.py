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

dash.register_page(__name__, path='/example')

layout = html.Div([
    html.H1("Example Page",
        className="title"),

    html.Div([
        html.P("Amount",
            className="slider-label"),

        dcc.Slider(id="Example_amount_slider", 
            min=10, 
            max=1000, 
            value=100, 
            step=10, 
            marks=None,
            tooltip={"placement": "bottom","always_visible": False})]),

    html.Br(),

    html.Div([
        html.Div([
            html.Div([
                dcc.Graph(id="Example_example_scatter_plot")],
                className="col-6"),

            html.Div([
                dcc.Graph(id="Example_example_line_plot")],
                className="col-6")],
            className="row")],
        className="container")])





@callback(
    Output(component_id="Example_example_scatter_plot", component_property="figure"),
    Input(component_id="Example_amount_slider", component_property="value"))
def update_Example_example_scatter_plot(Example_amount_input):
    __output_Example_example_scatter_plot_figure = px.scatter(model.get_data(Example_amount_input), x="x", y="y", title="Scatter Example")
    return __output_Example_example_scatter_plot_figure

@callback(
    Output(component_id="Example_example_line_plot", component_property="figure"),
    Input(component_id="Example_amount_slider", component_property="value"))
def update_Example_example_line_plot(Example_amount_input):
    __output_Example_example_line_plot_figure = px.line(model.get_data(Example_amount_input), x="x", y="y", title="Line Example")
    return __output_Example_example_line_plot_figure