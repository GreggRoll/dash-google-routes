# import googlemaps
import requests
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import base64
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import polyline


# Suppress the warnings if you decide to disable SSL verification
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Initialize the Google Maps API client
API_KEY = 'GOOGLE_API_KEY'
# gmaps = googlemaps.Client(key=API_KEY, requests_kwargs={'verify': False})

def get_route_df(start, end):
    # Get directions
    r = requests.get(f"https://maps.googleapis.com/maps/api/directions/json?key={API_KEY}&origin={start}&destination={end}&mode=driving", verify=False).json()
    
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

def get_street_view(lat, lng, heading=0, fov=180, pitch=0):
    # Construct a URL for the Street View Static API
    street_view_api_url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={lat},{lng}&heading={heading}&fov={fov}&pitch={pitch}&key={API_KEY}"

    r = requests.get(street_view_api_url, verify=False)

    if r.status_code == 200:
        # Image was successfully retrieved
        file_path = f"pics/streetview_{lat}_{lng}.jpg"
        with open(file_path, 'wb') as file:
            file.write(r.content)
        return file_path
    else:
        print(f"No Street View available at lat: {lat}, lng: {lng}")
        return None

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div([
        dcc.Input(id='route-start', type='text', placeholder='Enter start address', style={'width': '45%', 'margin-right': '5%'}),
        dcc.Input(id='route-end', type='text', placeholder='Enter end address', style={'width': '45%'}),
        html.Button('Submit', id='submit-button', n_clicks=0)
    ], style={'margin-bottom': '20px'}),
    dcc.Store(id='route-data-store'),
    dcc.Graph(id='map-plot', config={'displayModeBar': True}),
    html.Div(id='image-container', children=[html.Img(id='image', style={'width': '400px', 'height': 'auto'})]),
    dash_table.DataTable(
        id='data-table',
        columns=[],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
        page_size=10
    )
])

@app.callback(
    Output('route-data-store', 'data'),
    [Input('submit-button', 'n_clicks')],
    [State('route-start', 'value'), State('route-end', 'value')]
)
def generate_route_data(n_clicks, start, end):
    if n_clicks > 0 and start and end:
        if start == 'kosovo':
            route_df = pd.read_csv('kosovo_route.csv')
        elif start == 'greg':
            route_df = pd.read_csv('greg_route.csv')
        else:
            #Generate route dataframe
            route_df = get_route_df(start, end)
            
            for ix, row in route_df.iterrows():
                image_path = get_street_view(row['point_start_lat'], row['point_start_lng'])
                route_df.at[ix, 'image_path'] = image_path

        return route_df.to_dict()

    return {}

@app.callback(
    [Output('map-plot', 'figure'),
     Output('data-table', 'columns'),
     Output('data-table', 'data')],
    Input('route-data-store', 'data')
)
def update_map_and_table(route_data):
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
        line=dict(width=4, color='blue'),
        name='Route'
    ))

    # Overlay individual points with larger markers
    fig.add_trace(go.Scattermapbox(
        mode='markers',
        lon=route_df['point_start_lng'].tolist() + [route_df['point_end_lng'].iloc[-1]],
        lat=route_df['point_start_lat'].tolist() + [route_df['point_end_lat'].iloc[-1]],
        marker=dict(size=12, color='red'),  # Increased marker size
        name='Steps',
        customdata=route_df.index.tolist()  # Use this for custom data reference
    ))

    # Update the layout with a centered map
    fig.update_layout(
        mapbox=dict(
            style='open-street-map',
            center=dict(lon=polyline_lngs[0], lat=polyline_lats[0]),
            zoom=12
        ),
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    columns_to_display = ['html_instructions', 'distance', 'duration', 'maneuver']
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
    if not route_data or not clickData:
        return '', []

    route_df = pd.DataFrame(route_data)
    
    # Get the index of the clicked marker
    point_index = clickData['points'][0]['customdata']
    image_path = route_df.loc[point_index, 'image_path']
    image_src = encode_image(image_path)

    style_data_conditional = [{
        'if': {'row_index': point_index},
        'backgroundColor': '#FFDDC1',
        'color': 'black'
    }]

    return image_src, style_data_conditional

def encode_image(image_path):
    try:
        with open(image_path, 'rb') as f:
            return f"data:image/jpg;base64,{base64.b64encode(f.read()).decode()}"
    except Exception as e:
        print("Error encoding image:", str(e))
        return ''

#Uncomment below to run the app
if __name__ == '__main__':
    app.run_server(debug=True)
