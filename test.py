import folium
from pyproj import Transformer
import pandas as pd

def plot_on_openrailwaymap(df, lat_col, lon_col, map_name="OpenRailwayMap.html"):
    """
    Plots latitude and longitude data onto OpenRailwayMap using Folium.

    Parameters:
        df (pd.DataFrame): DataFrame containing latitude and longitude columns.
        lat_col (str): Name of the column with latitude values.
        lon_col (str): Name of the column with longitude values.
        map_name (str): File name for the saved map. Defaults to 'OpenRailwayMap.html'.

    Returns:
        None
    """
    # Check if required columns are present
    if lat_col not in df.columns or lon_col not in df.columns:
        raise ValueError(f"Columns '{lat_col}' and '{lon_col}' must exist in the DataFrame.")

    # Get the center of the map
    center_lat = df[lat_col].mean()
    center_lon = df[lon_col].mean()

    # Create the map centered on the data
    map_ = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Add OpenRailwayMap tile layer
    folium.TileLayer(
        tiles="https://tile.openrailwaymap.org/standard/{z}/{x}/{y}.png",
        attr="&copy; OpenRailwayMap contributors",
        name="OpenRailwayMap",
        overlay=True,
        control=True
    ).add_to(map_)

    # Plot each point
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row[lat_col], row[lon_col]],
            radius=3,
            color="red",
            fill=True,
            fill_opacity=0.8
        ).add_to(map_)

    # Save the map to an HTML file
    map_.save(map_name)
    print(f"Map saved as {map_name}")

# Example usage
# Example data with latitude and longitude
data = {
    "latitude": [52.5200, 48.8566, 51.1657],  # Berlin, Paris, Germany
    "longitude": [13.4050, 2.3522, 10.4515]
}
df = pd.DataFrame(data)

# Call the function
plot_on_openrailwaymap(df, lat_col="latitude", lon_col="longitude")
