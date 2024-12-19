import googlemaps
import requests
import pandas as pd
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress the warnings if you decide to disable SSL verification
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Initialize the client with your Google Maps API key
API_KEY = 'MY_API_KEY'
gmaps = googlemaps.Client(key=API_KEY, requests_kwargs={'verify': False})


def get_route_df(start_address, end_address):
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


def main(start, end):
    route_df = get_route_df(start, end)

    for ix, row in route_df.iterrows():
        image_path = get_street_view(
            row['point_start_lat'],
            row['point_start_lng']
        )
        route_df.at[ix, 'image_path'] = image_path

    return route_df


# Usage
start = "6801 S. Dale Mabry Hwy, MacDill AFB, FL"
end = "11076 Freedom Way, Seminole, FL"

route_df = main(start, end)
route_df.to_csv('route_df.csv')