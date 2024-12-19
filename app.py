import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import base64

route_df = pd.read_csv('route_df.csv')

# Create a Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Graph(
        id='map-plot',
        config={'displayModeBar': True}  # Enable displayModeBar for zoom buttons
    ),
])

@app.callback(
    Output('map-plot', 'figure'),
    Input('map-plot', 'hoverData')
)
def display_map(hoverData):
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

    # Check for hoverData and add image overlay to hover tooltip
    if hoverData:
        point_index = hoverData['points'][0]['pointIndex']
        image_path = route_df.loc[point_index, 'image_path']
        encoded_image_uri = encode_image(image_path)

        fig.update_traces(
            hovertemplate=(
                f'<img src="{encoded_image_uri}" style="width:200px;"><br>%{{hovertext}}'
            ),
            selector=dict(mode='markers')
        )

    return fig

def encode_image(image_path):
    try:
        with open(image_path, 'rb') as f:
            return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"
    except Exception as e:
        print(str(e))
        return ''

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
