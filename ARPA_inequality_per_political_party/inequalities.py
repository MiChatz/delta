import dash
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px

from dash import dcc, html
from .data.get_data import extract_data

class Inequalities():
    START = 'Start'
    STOP  = 'Stop'

    def __init__(self, application = None):
        self.df = extract_data()
        self.color = {'Gauche': 'indianred', 'Centre': 'goldenrod', 'Droite': 'darkcyan'}
        self.years = self.df.year.unique()

        self.main_layout = html.Div(children=[
            html.H3(children='Répartition des inéqualités par parti politique en Europe'),

            html.Div([
                    html.Div([ dcc.Graph(id='ine-main-graph')]),
                    
                    html.Div([
                        html.Br(),
                        html.Br(),
                        html.Div('Orientation politique', style={'font-weight': 'bold'}),
                        dcc.Checklist(
                            id='ine-crossfilter-which-party',
                            options=[{'label': " " + i, 'value': i} for i in sorted(self.color.keys())],
                            value=sorted(self.color.keys()),
                            labelStyle={'display':'block'},
                        )
                    ], style={'margin-left':'90px', 'float':'right'}),
                ], style={
                    'display':'flex',
                    'justifyContent':'center'
                }),

            html.Div([
                    html.Div(
                        dcc.Slider(
                                id='ine-crossfilter-year-slider',
                                min=self.years[0],
                                max=self.years[-1],
                                step = 1,
                                value=self.years[0],
                                marks={str(year): str(year) for year in self.years[::3]},
                        ),
                        style={'width':"60%", 'margin-right': '40px'}
                    ),
                    dcc.Interval(            # fire a callback periodically
                        id='ine-auto-stepper',
                        interval=750,       # in milliseconds
                        max_intervals = -1,  # start running
                        n_intervals = 0
                    ),
                    html.Button(
                            self.START,
                            id='ine-button-start-stop', 
                    )
                ], style={
                    'display': 'flex',
                    'justifyContent':'center',
                    'margin-right': '110px'
                }),
            html.Br(),
            html.Div(id='ine-div-country'),
            html.Div([
                    dcc.Graph(id='ine-gini-evolution',
                              style={'width':'50%', 'display':'inline-block'}),
                    dcc.Graph(id='ine-mean-gini-per-party',
                              style={'width':'50%', 'display':'inline-block'}),
                ], style={ 'display':'flex', 
                           'borderTop': 'thin lightgrey solid',
                           'borderBottom': 'thin lightgrey solid',
                           'justifyContent':'center' }),
        ], style={'padding': '10px 50px 10px 50px'})
        
        if application:
            self.app = application
            # application should have its own layout and use self.main_layout as a page or in a component
        else:
            self.app = dash.Dash(__name__)
            self.app.layout = self.main_layout
        
        self.app.callback(
            dash.dependencies.Output('ine-main-graph', 'figure'),
            [dash.dependencies.Input('ine-crossfilter-which-party', 'value'),
            dash.dependencies.Input('ine-crossfilter-year-slider', 'value')])(self.update_graph)
        self.app.callback(
            dash.dependencies.Output('ine-button-start-stop', 'children'),
            dash.dependencies.Input('ine-button-start-stop', 'n_clicks'),
            dash.dependencies.State('ine-button-start-stop', 'children'))(self.button_on_click)
        # this one is triggered by the previous one because we cannot have 2 outputs for the same callback
        self.app.callback(
            dash.dependencies.Output('ine-auto-stepper', 'max_interval'),
            [dash.dependencies.Input('ine-button-start-stop', 'children')])(self.run_movie)
        # triggered by previous
        self.app.callback(
            dash.dependencies.Output('ine-crossfilter-year-slider', 'value'),
            dash.dependencies.Input('ine-auto-stepper', 'n_intervals'),
            [dash.dependencies.State('ine-crossfilter-year-slider', 'value'),
             dash.dependencies.State('ine-button-start-stop', 'children')])(self.on_interval)
        self.app.callback(
            dash.dependencies.Output('ine-div-country', 'children'),
            dash.dependencies.Input('ine-main-graph', 'hoverData'))(self.get_country)
        self.app.callback(
            dash.dependencies.Output('ine-gini-evolution', 'figure'),
            [dash.dependencies.Input('ine-main-graph', 'hoverData')])(self.update_gini_evolution)
        self.app.callback(
            dash.dependencies.Output('ine-mean-gini-per-party', 'figure'),
            [dash.dependencies.Input('ine-main-graph', 'hoverData')])(self.update_mean_gini_per_party)

    def update_graph(self, parties, year):
        dfg = self.df[self.df.year == year]
        dfg = dfg[dfg['Main Party'].isin(parties)]

        if dfg.empty:
            fig = go.Figure(go.Scattergeo())
        else:
            fig = px.scatter_geo(dfg, locations="iso", hover_name="country", hover_data=['gini'],
                                 size="gini_display", color='Main Party', color_discrete_map=self.color,
                                 opacity=0.95)
        fig.update_geos(
            resolution=50,
            showcoastlines=True, coastlinecolor="RebeccaPurple",
            showland=True, landcolor="MediumSeaGreen",
            showocean=True, oceancolor="LightSkyBlue",
            scope='europe', projection_type='natural earth'
        )
        fig.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
        return fig

    def update_gini_evolution(self, hover_data):
        country = self.get_country(hover_data)
        dfg = self.df[self.df.country == country]
        offset = 0.025

        fig = go.Figure()
        for index, row in dfg.reset_index().iterrows():
            previous_year = 2000 if index == 0 else dfg.iloc[[index - 1]].year
            previous_gini = dfg.iloc[[0]].gini if index == 0 else dfg.iloc[[index - 1]].gini
            fig.add_trace(go.Scatter(x=[int(previous_year), row.year], y=[float(previous_gini), row.gini],
                                     fill='tozeroy', fillcolor=self.color[row['Main Party']], line_color=self.color[row['Main Party']], text=row['Main Party']))
        fig.update_layout(showlegend=False, yaxis_range=[dfg['gini'].min() - offset, dfg['gini'].max() + offset])
        
        return fig
    
    def update_mean_gini_per_party(self, hover_data):
        country = self.get_country(hover_data)
        dfg = self.df[self.df.country == country]
        dfg = dfg.groupby('Main Party')['gini'].mean().to_frame(name='mean').reset_index()
        fig = px.bar(dfg, x='Main Party', y='mean')
        fig.update_layout(hovermode='closest')
        return fig

    def get_country(self, hover_data):
        if hover_data == None:  # init value
            return self.df['country'].iloc[np.random.randint(len(self.df))]
        return hover_data['points'][0]['hovertext']

    # start and stop the movie
    def button_on_click(self, n_clicks, text):
        if text == self.START:
            return self.STOP
        return self.START

    # this one is triggered by the previous one because we cannot have 2 outputs
    # in the same callback
    def run_movie(self, text):
        if text == self.START:    # then it means we are stopped
            return 0 
        return -1

    # see if it should move the slider for simulating a movie
    def on_interval(self, n_intervals, year, text):
        if text == self.STOP:  # then we are running
            if year == self.years[-1]:
                return self.years[0]
            return year + 1
        return year  # nothing changes

    def run(self, debug=False, port=8050):
        self.app.run_server(host="0.0.0.0", debug=debug, port=port)


if __name__ == '__main__':
    ineq = Inequalities()
    ineq.run(port=8055)