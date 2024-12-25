import base64
import os

import requests
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import polyline
from dotenv import load_dotenv
from PIL import Image
import re

# Suppress the warnings if you decide to disable SSL verification
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

load_dotenv()
API_KEY = os.getenv('GOOGLE_API')

def merge_images(file1, file2, file3):
    """Merge three images into one, displayed side by side
    :param file1: path to first image file
    :param file2: path to second image file
    :param file3: path to third image file
    :return: the merged Image object
    """
    image1 = Image.open(file1)
    image2 = Image.open(file2)
    image3 = Image.open(file3)

    (width1, height1) = image1.size
    (width2, height2) = image2.size
    (width3, height3) = image3.size

    result_width = width1 + width2 + width3
    result_height = max(height1, height2, height3)

    result = Image.new('RGB', (result_width, result_height))
    result.paste(im=image1, box=(0, 0))
    result.paste(im=image2, box=(width1, 0))
    result.paste(im=image3, box=(width1 + width2, 0))
    return result

def get_route_df(start_address, end_address):
    """Fetch route data from Google Maps API and return it as a DataFrame.
    :param start_address: The starting address for the route.
    :param end_address: The ending address for the route.
    :return: DataFrame containing route information.
    """
    # Get directions
    r = requests.get(f"https://maps.googleapis.com/maps/api/directions/json?key={API_KEY}&origin={start_address}&destination={end_address}&mode=driving", verify=False, timeout=10).json()
    
    df = pd.DataFrame(r['routes'][0]['legs'][0]['steps'])
    df['overview_polyline'] = r['routes'][0]['overview_polyline']['points']
    df['total_distance'] = r['routes'][0]['legs'][0]['distance']['text']
    df['total_duration'] = r['routes'][0]['legs'][0]['duration']['text']
    df['start_address'] = r['routes'][0]['legs'][0]['start_address']
    df['end_address'] = r['routes'][0]['legs'][0]['end_address']
    df['point_start_lat'] = df['start_location'].apply(lambda x: x['lat'])
    df['point_start_lng'] = df['start_location'].apply(lambda x: x['lng'])
    df['point_end_lat'] = df['end_location'].apply(lambda x: x['lat'])
    df['point_end_lng'] = df['end_location'].apply(lambda x: x['lng'])
    df['distance'] = df['distance'].apply(lambda x: x['text'])
    df['duration'] = df['duration'].apply(lambda x: x['text'])
    df['polyline'] = df['polyline'].apply(lambda x: x['points'])

    df.drop(columns=['end_location', 'start_location'], inplace=True)

    return df

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

app.layout = html.Div([
    html.Div([
        html.H1("Route Planner", style={'textAlign': 'center', 'color': 'white'}),
        html.Div([
            dcc.Input(id='route-start', type='text', placeholder='Enter start address', style={'width': '45%', 'margin-right': '5%'}),
            dcc.Input(id='route-end', type='text', placeholder='Enter end address', style={'width': '45%'}),
            html.Button('Submit', id='submit-button', n_clicks=0, style={'margin-left': '10px'})
        ], style={'display': 'flex', 'justify-content': 'center', 'align-items': 'center', 'margin-bottom': '20px'}),
        html.Div(id='route-info', style={'textAlign': 'center', 'color': 'white', 'margin-bottom': '20px'}),
    ], style={'backgroundColor': '#333', 'padding': '20px'}),
    dcc.Store(id='route-data-store'),
    dcc.Graph(id='map-plot', config={'displayModeBar': True}),
    html.Div(id='image-container', children=[html.Img(id='image', style={'width': '100%', 'height': 'auto'})]),
    dash_table.DataTable(
        id='data-table',
        columns=[],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'backgroundColor': '#333', 'color': 'white'},
        style_header={'backgroundColor': '#444', 'color': 'white'},
        page_size=30
    ),
    html.Button('Generate GregGreg', id='generate-greggreg-button', n_clicks=0, style={'width': '100%', 'padding': '20px', 'backgroundColor': '#444', 'color': 'white', 'fontSize': '20px', 'margin-top': '20px'}),
    html.Div(id='greggreg-report', style={'margin-top': '20px', 'color': 'white'})
], style={'backgroundColor': '#222', 'color': 'white', 'font-family': 'Arial, sans-serif'})

@app.callback(
    [Output('route-data-store', 'data'),
     Output('route-info', 'children')],
    [Input('submit-button', 'n_clicks')],
    [State('route-start', 'value'), State('route-end', 'value')]
)
def generate_route_data(n_clicks, start, end):
    """Generate route data and save images for the route.
    :param n_clicks: Number of times the submit button has been clicked.
    :param start: Starting address for the route.
    :param end: Ending address for the route.
    :return: Dictionary representation of the route DataFrame and route info.
    """
    if n_clicks > 0 and start and end:
        print('starting route generation')
        if start == 'kosovo':
            route_df = pd.read_csv('kosovo_route.csv')
        elif start == 'greg':
            route_df = pd.read_csv('greg_route.csv')
        else:
            route_df = get_route_df(start, end)
            print('completed route generation, starting image generation')
            for ix, row in route_df.iterrows():
                lat = row['point_start_lat']
                lng = row['point_start_lng']
                heading=0
                fov=120
                street_view_api_url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={API_KEY}"
                r = requests.get(street_view_api_url, verify=False, timeout=10)
                if r.status_code == 200:
                    route_df.at[ix, 'imagery_date'] = r.json()['date']
                    for i in range(3):
                        street_view_api_url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={lat},{lng}&heading={heading}&fov={fov}&pitch=0&key={API_KEY}&radius=50&return_error_code=true&source=outdoor"
                        rr = requests.get(street_view_api_url, verify=False, timeout=10)
                        file_path = f"pics/streetview_{lat}_{lng}_{heading}.jpg"
                        
                        with open(file_path, 'wb') as file:
                            file.write(rr.content)
                        route_df.at[ix, f'image_{i+1}'] = file_path
                        heading += 120

                pano = merge_images(route_df['image_1'][ix], route_df['image_2'][ix], route_df['image_3'][ix])
                file_path = f"pics/streetview_{lat}_{lng}_pano.jpg"
                pano.save(f"pics/streetview_{lat}_{lng}_pano.jpg")
                route_df.at[ix, 'pano'] = file_path
                print(f'Completed image generation {ix+1}/{len(route_df)}')
        
        route_info = [
            html.Div(f"Total Distance: {route_df['total_distance'].iloc[0]}"),
            html.Div(f"Total Duration: {route_df['total_duration'].iloc[0]}")
        ]
        return route_df.to_dict(), route_info

    return {}, []

@app.callback(
    [Output('map-plot', 'figure'),
     Output('data-table', 'columns'),
     Output('data-table', 'data')],
    Input('route-data-store', 'data')
)
def update_map_and_table(route_data):
    """Update the map and data table based on the route data.
    :param route_data: Dictionary representation of the route DataFrame.
    :return: Updated map figure, table columns, and table data.
    """
    if not route_data or 'overview_polyline' not in route_data:
        return go.Figure(), [], []  # Return empty graph and table

    route_df = pd.DataFrame(route_data)
    
    # Decode the overview polyline
    polyline_points = polyline.decode(route_df['overview_polyline'].iloc[0])
    polyline_lats, polyline_lngs = zip(*polyline_points)

    # Create a figure with the polyline
    fig = go.Figure(go.Scattermapbox(
        mode='lines',
        lon=polyline_lngs,
        lat=polyline_lats,
        line={'width': 4, 'color': 'blue'},
        name='Route'
    ))

    # Overlay individual points with larger markers
    fig.add_trace(go.Scattermapbox(
        mode='markers',
        lon=route_df['point_start_lng'].tolist() + [route_df['point_end_lng'].iloc[-1]],
        lat=route_df['point_start_lat'].tolist() + [route_df['point_end_lat'].iloc[-1]],
        marker={'size': 12, 'color': 'red'},  # Increased marker size
        name='Steps',
        customdata=route_df.index.tolist()  # Use this for custom data reference
    ))

    # Update the layout with a centered map
    fig.update_layout(
        mapbox={
            'style': 'open-street-map',
            'center': dict(lon=polyline_lngs[0], lat=polyline_lats[0]),
            'zoom': 12
        },
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    columns_to_display = ['html_instructions', 'distance', 'duration', 'maneuver', 'date']
    columns = [{"name": i, "id": i} for i in columns_to_display if i in route_df.columns]
    data = route_df.to_dict('records')
    
    return fig, columns, data

@app.callback(
    [Output('image', 'src'),
     Output('data-table', 'style_data_conditional')],
    Input('map-plot', 'clickData'),
    State('route-data-store', 'data')
)
def update_image_and_highlight_row(clickData, route_data):
    """Update the displayed image and highlight the corresponding row in the table.
    :param clickData: Data from the clicked point on the map.
    :param route_data: Dictionary representation of the route DataFrame.
    :return: Base64 encoded image source and style data for the table.
    """
    if not route_data or not clickData:
        return '', []

    route_df = pd.DataFrame(route_data)
    
    # Get the index of the clicked marker
    point_index = clickData['points'][0]['pointIndex']

    image_path = route_df.loc[str(point_index), 'pano']
    with open(image_path, 'rb') as f:
        image_src = f"data:image/jpg;base64,{base64.b64encode(f.read()).decode()}"

    style_data_conditional = [{
        'if': {'row_index': point_index},
        'backgroundColor': '#FFDDC1',
        'color': 'black'
    }]

    return image_src, style_data_conditional


@app.callback(
    Output('greggreg-report', 'children'),
    Input('generate-greggreg-button', 'n_clicks'),
    State('route-data-store', 'data')
)
def generate_greggreg_report(n_clicks, route_data):
    """Generate an HTML report similar to a MapQuest report.
    :param n_clicks: Number of times the Generate GregGreg button has been clicked.
    :param route_data: Dictionary representation of the route DataFrame.
    :return: HTML report as a list of Dash HTML components.
    """
    if n_clicks > 0 and route_data:
        route_df = pd.DataFrame(route_data)
        report = [
            html.H2(f"{route_df['start_address'].iloc[0]} - {route_df['end_address'].iloc[0]}"),
            html.Div(f"Total Distance: {route_df['total_distance'].iloc[0]}"),
            html.Div(f"Total Duration: {route_df['total_duration'].iloc[0]}"),
            html.Hr()
        ]

        for ix, row in route_df.iterrows():
            with open(row['pano'], 'rb') as f:
                image_src = f"data:image/jpg;base64,{base64.b64encode(f.read()).decode()}"

            instructions = row['html_instructions']
            cleaned_instructions = re.sub(r'<.*?>', '', instructions)

            report.append(html.Div([
                #html.Div(dcc.Markdown(row['html_instructions']), style={'margin-bottom': '10px'}),
                html.Div(cleaned_instructions, style={'margin-bottom': '10px'}),
                html.Div(f"Distance: {row['distance']}"),
                html.Div(f"Duration: {row['duration']}"),
                html.Div(f"Maneuver: {row['maneuver']}"),
                html.Img(src=image_src, style={'width': '100%', 'height': 'auto', 'margin-top': '10px'}),
                html.Hr()
            ], style={'margin-bottom': '20px'}))

        return report

    return []

# Uncomment below to run the app
if __name__ == '__main__':
    app.run_server(debug=True)
