import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import base64

route_df = pd.read_csv('route_df.csv')

# Columns to display in the DataTable
columns_to_display = ['html_instructions', 'distance', 'duration', 'maneuver']

# Create a Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Store(id='map-figure-store'),
    html.Div(id='header-container', style={'margin-bottom': '20px'}),
    dcc.Graph(
        id='map-plot',
        config={'displayModeBar': True}  # Enable displayModeBar for zoom buttons
    ),
    html.Div(id='image-container', children=[
        html.Img(id='image', style={'width': '400px', 'height': 'auto'})
    ]),
    dash_table.DataTable(
        id='data-table',
        columns=[{"name": i, "id": i} for i in columns_to_display],
        data=route_df[columns_to_display].to_dict('records'),
        style_data_conditional=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        page_size=10
    )
])

@app.callback(
    Output('map-figure-store', 'data'),
    Input('map-plot', 'id')  # Dummy input to trigger the callback once
)
def generate_map(_):
    # Prepare the plot
    fig = px.scatter_mapbox(
        route_df,
        lat='point_start_lat',
        lon='point_start_lng',
        hover_name='start_address',
        hover_data={'point_start_lat': False, 'point_start_lng': False},
        zoom=14,
        height=600
    )

    # Add a line connecting the points
    fig.add_trace(go.Scattermapbox(
        lat=route_df['point_start_lat'],
        lon=route_df['point_start_lng'],
        mode='lines+markers',
        marker={'size': 10, 'color': 'blue'},
        line={'width': 2, 'color': 'blue'}
    ))

    # Update layout for mapbox
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )

    return fig

@app.callback(
    Output('map-plot', 'figure'),
    Input('map-figure-store', 'data')
)
def update_map(figure):
    return figure

@app.callback(
    [Output('image', 'src'),
     Output('data-table', 'style_data_conditional'),
     Output('header-container', 'children')],
    Input('map-plot', 'clickData')
)
def update_image_and_highlight_row(clickData):
    # Default image source and style
    image_src = ''
    style_data_conditional = []
    header_content = generate_header_content(route_df.iloc[0])

    # Check for clickData and update image source and row highlight
    if clickData:
        print("Click Data:", clickData)  # Debugging print statement
        point_index = clickData['points'][0]['pointIndex']
        image_path = route_df.loc[point_index, 'image_path']
        print("Image Path:", image_path)  # Debugging print statement
        image_src = encode_image(image_path)
        print("Encoded Image URI:", image_src)  # Debugging print statement

        # Highlight the selected row
        style_data_conditional = [{
            'if': {'row_index': point_index},
            'backgroundColor': '#FFDDC1',
            'color': 'black'
        }]

        # Update header content with the selected row's data
        header_content = generate_header_content(route_df.iloc[point_index])

    return image_src, style_data_conditional, header_content

def encode_image(image_path):
    try:
        with open(image_path, 'rb') as f:
            return f"data:image/jpg;base64,{base64.b64encode(f.read()).decode()}"
    except Exception as e:
        print("Error encoding image:", str(e))  # Debugging print statement
        return ''

def generate_header_content(row):
    return html.Div([
        html.H3("Route Information"),
        html.P(f"Start Address: {row['start_address']}"),
        html.P(f"End Address: {row['end_address']}"),
        html.P(f"Total Distance: {row['total_distance']} km"),
        html.P(f"Total Duration: {row['total_duration']} minutes")
    ])

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
