import os

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import TimestampedGeoJson
from matplotlib import colormaps, colors
from branca.colormap import LinearColormap

def generate_map_from_csv(subset_full_path):
    # -------------------------------------------------------------------------
    # 1. Load and Preprocess Data
    # -------------------------------------------------------------------------
    file_path = subset_full_path

    # Extract the directory of the CSV file
    base_dir = os.path.dirname(file_path)
    file_path = subset_full_path
    df = pd.read_csv(file_path, parse_dates=["DatumZeit"])
    df = df.sort_values(by="DatumZeit")

    # Convert speed from m/s to km/h if needed
    if "Geschwindigkeit in m/s" in df.columns:
        df["Speed_kmh"] = df["Geschwindigkeit in m/s"] * 3.6
    else:
        df["Speed_kmh"] = 0.0

    if df.empty:
        raise ValueError("No data after filtering. Check your CSV or filter settings.")

    # Extract date from first row
    day_display = df["DatumZeit"].dt.date.iloc[0]

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(lon, lat) for lon, lat in zip(df["GPS_lon"], df["GPS_lat"])],
        crs="EPSG:4326"
    )

    # -------------------------------------------------------------------------
    # 2. Initialize the Map
    # -------------------------------------------------------------------------
    start_lat, start_lon = gdf.iloc[0].geometry.y, gdf.iloc[0].geometry.x
    m = folium.Map(location=[start_lat, start_lon], zoom_start=14, tiles=None)

    # -------------------------- OpenRailwayMap Layers -------------------------
    layers = {
        "Standard": "https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
        "Electrified": "https://{s}.tiles.openrailwaymap.org/electrified/{z}/{x}/{y}.png",
        "Signals": "https://{s}.tiles.openrailwaymap.org/signals/{z}/{x}/{y}.png",
    }

    # Make "Standard" the base layer
    folium.TileLayer(
        tiles=layers["Standard"],
        attr="&copy; OpenRailwayMap contributors",
        name="OpenRailwayMap - Standard (Base)",
        overlay=False,  # Base layer
        control=True
    ).add_to(m)

    # Add the other layers as overlays
    for layer_name, layer_url in layers.items():
        if layer_name == "Standard":
            continue  # Already added as base
        folium.TileLayer(
            tiles=layer_url,
            attr="&copy; OpenRailwayMap contributors",
            name=f"OpenRailwayMap - {layer_name}",
            overlay=True
        ).add_to(m)

    # -------------------------------------------------------------------------
    # 4A. Uniform-colored Path FeatureGroup
    # -------------------------------------------------------------------------
    uniform_path_fg = folium.FeatureGroup(name="Path", show=True)

    for i in range(len(gdf) - 1):
        lat1, lon1 = gdf.iloc[i].geometry.y, gdf.iloc[i].geometry.x
        lat2, lon2 = gdf.iloc[i + 1].geometry.y, gdf.iloc[i + 1].geometry.x

        folium.PolyLine(
            [(lat1, lon1), (lat2, lon2)],
            color="blue",  # or any single color you like
            weight=5,
            opacity=0.7
        ).add_to(uniform_path_fg)

    uniform_path_fg.add_to(m)

    # -------------------------------------------------------------------------
    # 4B. Speed-colored Path FeatureGroup
    # -------------------------------------------------------------------------
    speed_path_fg = folium.FeatureGroup(name="Speed Path", show=False)

    speed_min, speed_max = gdf["Speed_kmh"].min(), gdf["Speed_kmh"].max()
    norm = colors.Normalize(vmin=speed_min, vmax=speed_max)
    cmap = colormaps.get_cmap("turbo")  # "viridis", "plasma", "turbo", etc.

    for i in range(len(gdf) - 1):
        lat1, lon1 = gdf.iloc[i].geometry.y, gdf.iloc[i].geometry.x
        lat2, lon2 = gdf.iloc[i + 1].geometry.y, gdf.iloc[i + 1].geometry.x
        speed_val = gdf.iloc[i]["Speed_kmh"]
        color = colors.to_hex(cmap(norm(speed_val)))

        folium.PolyLine(
            [(lat1, lon1), (lat2, lon2)],
            color=color,
            weight=5,
            opacity=0.7
        ).add_to(speed_path_fg)

    speed_path_fg.add_to(m)

    # -------------------------------------------------------------------------
    # 5. Start & End Markers
    # -------------------------------------------------------------------------
    start_point = (gdf.iloc[0].geometry.y, gdf.iloc[0].geometry.x)
    end_point = (gdf.iloc[-1].geometry.y, gdf.iloc[-1].geometry.x)

    folium.Marker(
        location=start_point,
        popup=f"Start Point<br>Date: {day_display}",
        icon=folium.Icon(color="green")
    ).add_to(m)

    folium.Marker(
        location=end_point,
        popup=f"End Point<br>Date: {day_display}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # -------------------------------------------------------------------------
    # 6. Title / Date Box
    # -------------------------------------------------------------------------
    title_html = f"""
        <div style="position: fixed; top: 10px; left: 50px; width: 160px; 
                    background-color: white; z-index: 9999; font-size: 16px; 
                    border: 2px solid black; padding: 10px;">
            <b>Date:</b> {day_display}
        </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    # -------------------------------------------------------------------------
    # 7. Speed Colormap Legend (for the speed path)
    # -------------------------------------------------------------------------
    color_steps = range(int(speed_min), int(speed_max) + 1, 10)
    color_list  = [colors.to_hex(cmap(norm(v))) for v in color_steps]
    colormap = LinearColormap(
        colors=color_list,
        vmin=speed_min,
        vmax=speed_max,
        caption="Speed (km/h)"
    )
    colormap.add_to(m)

    # ------- 8. OPTIONAL: Time-Animated Single Marker (Directly to the Map) -------
    features = []
    for _, row in gdf.iterrows():
        lat, lon = row.geometry.y, row.geometry.x
        time_str = row["DatumZeit"].isoformat()
        speed_val = row["Speed_kmh"]

        popup_text = (f"<b>Time:</b> {row['DatumZeit']}<br>"
                      f"<b>Speed:</b> {speed_val:.2f} km/h")

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "time": time_str,
                "popup": popup_text,
                "style": {"color": "black", "fillColor": "black"},
                "icon": "circle"
            }
        }
        features.append(feature)

    if features:
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        animated_marker = TimestampedGeoJson(
            data=geojson_data,
            transition_time=500,  # milliseconds between steps
            loop=False,
            auto_play=False,
            add_last_point=True,
            period="PT10S",  # Adjust as needed
            duration="PT1S"
        )
        animated_marker.add_to(m)  # Add directly to the Map without FeatureGroup

    # -------------------------------------------------------------------------
    # 9. Layer Control
    # -------------------------------------------------------------------------
    folium.LayerControl(collapsed=False).add_to(m)

    # -------------------------------------------------------------------------
    # 10. Save the Map
    # -------------------------------------------------------------------------
    output_file = os.path.join(base_dir, f"map_{day_display}.html")
    m.save(output_file)
    print(f"Map saved as '{output_file}'. Open it in your browser to view!")
