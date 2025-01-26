#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module: Data Tools
Description: Provides utilities for geospatial calculations and data transformations,
including coordinate projections and distance computations.
"""

import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter


def data_convert_to_planar(df, config):
    """
    Add UTM coordinates to the DataFrame based on latitude and longitude using vectorized operations.
    Prioritize smoothed columns if available, otherwise use the original columns.

    If multiple smoothed columns are available, allow the user to select one via a GUI.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame with GPS data.
    config : dict
        Configuration dictionary with column names and transformation settings.

    Returns
    -------
    pd.DataFrame
        DataFrame with added planar coordinates (x, y) and a column for the selected smoothing method.
    """
    # Identify smoothed latitude and longitude columns
    smoothed_lat_columns = [
        col for col in df.columns if col.startswith("GPS_lat_smooth_")
    ]
    smoothed_lon_columns = [
        col.replace("GPS_lat", "GPS_lon") for col in smoothed_lat_columns
    ]

    # Initialize selected method
    selected_method = "none"  # Default to raw columns if no smoothing is applied

    # Determine which columns to use
    if len(smoothed_lat_columns) > 1:
        # Show a GUI to let the user choose
        root = tk.Tk()
        root.title("Select Smoothing Algorithm")

        selected_method_var = tk.StringVar(
            value=smoothed_lat_columns[0].split("_")[-1]
        )  # Default to the first method

        def submit():
            root.destroy()

        # Add a label and dropdown menu
        tk.Label(root, text="Choose a smoothing method:").pack(pady=10)
        dropdown = ttk.Combobox(
            root,
            textvariable=selected_method_var,
            values=[col.split("_")[-1] for col in smoothed_lat_columns],
            state="readonly",
        )
        dropdown.pack(pady=10)

        # Add a submit button
        tk.Button(root, text="Submit", command=submit).pack(pady=10)

        # Run the GUI
        root.mainloop()

        selected_method = selected_method_var.get()

        # Validate the user input
        lat_col = f"GPS_lat_smooth_{selected_method}"
        lon_col = f"GPS_lon_smooth_{selected_method}"
        if lat_col not in df.columns or lon_col not in df.columns:
            raise ValueError(
                f"Invalid selection: {selected_method}. "
                f"Columns {lat_col} and {lon_col} not found."
            )
        print(f"Using smoothed columns: {lat_col}, {lon_col}")
    elif len(smoothed_lat_columns) == 1:
        # Use the single available smoothed column
        lat_col = smoothed_lat_columns[0]
        lon_col = smoothed_lon_columns[0]
        selected_method = lat_col.split("_")[-1]
        print(f"Automatically using smoothed columns: {lat_col}, {lon_col}")
    else:
        # Fall back to raw data columns specified in config
        lat_col = config["lat_col"]
        lon_col = config["lon_col"]
        print(f"No smoothed GPS columns found. Using raw data columns: {lat_col}, {lon_col}")

    # Transformer: WGS84 (EPSG:4326) to UTM zone 33N (EPSG:32633)
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True)
    x, y = transformer.transform(df[lon_col].values, df[lat_col].values)

    # Add planar coordinates to the DataFrame
    df["x"] = x
    df["y"] = y

    # Add the selected smoothing method to the DataFrame
    df["selected_smoothing_method"] = selected_method

    return df


def data_filter_points_by_distance(df, config):
    """
    Filter points by a minimum distance using columns and settings from config.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame containing coordinates.
    config : dict
        Dictionary containing configuration values:
            - "x_col": Column name for x-coordinates.
            - "y_col": Column name for y-coordinates.
            - "min_distance": Minimum distance to retain a point.

    Returns
    -------
    pd.DataFrame
        Modified DataFrame with points spaced by at least the minimum distance
        and a new column 'min_distance' indicating the distance used for filtering.
    """
    x_col = config["x_col"]
    y_col = config["y_col"]
    min_distance = config["min_distance"]

    # Check if the DataFrame is empty
    if df.empty:
        return df

    # Validate required columns
    for col in [x_col, y_col]:
        if col not in df.columns:
            raise ValueError(
                f"Missing column '{col}'. Ensure planar coordinates exist before calling this function."
            )

    # Extract coordinates as a NumPy array
    coords = df[[x_col, y_col]].to_numpy()

    # Initialize list of retained indices
    retained_indices = [0]  # Always keep the first point
    last_retained_point = coords[0]  # Start with the first point

    # Iterate through the remaining points
    for i in range(1, len(coords)):
        distance = np.linalg.norm(coords[i] - last_retained_point)  # Distance to last retained point
        if distance >= min_distance:
            retained_indices.append(i)  # Retain the current point
            last_retained_point = coords[i]  # Update the last retained point

    # Filter the DataFrame
    df = df.iloc[retained_indices].reset_index(drop=True)

    # Add min_distance as a new column for all rows
    df['min_distance'] = min_distance

    return df

def parse_time_and_compute_dt(df, datetime_col):
    """
    Parse the given datetime column as pandas datetime and compute delta time (in seconds).

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    datetime_col : str
        Name of the column containing datetime information.

    Returns
    -------
    pd.DataFrame
        A copy of the DataFrame with a new column 'dt' containing time differences in seconds.
    """
    df = df.copy()

    # Convert the column to datetime
    df[datetime_col] = pd.to_datetime(df[datetime_col])

    # Compute the difference in timestamps
    df["dt"] = df[datetime_col].diff().dt.total_seconds()

    return df


def data_compute_heading_from_xy(df, config):
    """
    Compute heading for each row based on consecutive (x, y) points.
    Heading is computed using arctan2(dy, dx) and returned in degrees within [0, 360).

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing at least the x_col and y_col specified in config.
    config : dict
        Configuration dictionary containing keys:
            - "x_col": Column name for the x-coordinate (default "x").
            - "y_col": Column name for the y-coordinate (default "y").
            - "heading_col": Name of the new column for heading (default "heading_deg").

    Returns
    -------
    pd.DataFrame
        The modified DataFrame with the new column for heading.
    """
    # Extract column names from config
    x_col = config.get("x_col", "x")
    y_col = config.get("y_col", "y")
    heading_col = config.get("heading_col", "heading_deg")

    # Check if required columns exist
    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError(f"Required columns '{x_col}' and/or '{y_col}' not found in DataFrame.")

    # Calculate differences
    dx = df[x_col].diff()
    dy = df[y_col].diff()

    # Compute heading in radians
    heading_rad = np.arctan2(dy, dx)  # range: [-pi, pi]

    # Convert to degrees and shift to [0, 360)
    heading_deg = np.degrees(heading_rad)
    heading_deg = (heading_deg + 360) % 360

    # Assign to the specified column
    df[heading_col] = heading_deg

    return df


def data_compute_yaw_rate_from_heading(df, config):
    """
    Calculate yaw rate in degrees/second given an existing heading column (in degrees)
    and a time-delta column (in seconds).

    Steps:
        1. Take the difference of consecutive headings (heading_col.diff()).
        2. Wrap the heading difference to stay within [-180, 180].
        3. Divide by dt to get yaw rate in degrees/second.
        4. Store the result in a fixed column name 'yaw_rate_deg_s'.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing heading_col and dt_col.
    config : dict
        Configuration dictionary containing keys:
            - "heading_col": Column name containing heading in degrees (default "heading_deg").
            - "dt_col": Column name containing time deltas in seconds (default "dt").

    Returns
    -------
    pd.DataFrame
        The modified DataFrame with an additional column 'yaw_rate_deg_s' for yaw rate.
    """
    # Extract column names from config
    heading_col = config.get("heading_col", "heading_deg")
    dt_col = config.get("dt_col", "dt")

    # Ensure required columns exist
    if heading_col not in df.columns or dt_col not in df.columns:
        raise ValueError(f"Required columns '{heading_col}' and/or '{dt_col}' not found in DataFrame.")

    # 1. Heading difference
    heading_diff = df[heading_col].diff()

    # 2. Wrap to [-180, 180]
    heading_diff = (heading_diff + 180) % 360 - 180

    # 3. Divide by dt => degrees/second
    dt_vals = df[dt_col]
    yaw_rate_deg_s = heading_diff / dt_vals

    # 4. Assign to a fixed column name
    df["yaw_rate_deg_s"] = yaw_rate_deg_s

    return df

def data_smooth_gps_savitzky(df, config):
    """
    Smooth the GPS latitude and longitude data using a Savitzky-Golay filter.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame with GPS data.
    config : dict
        Configuration dictionary containing column names and settings.

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with smoothed GPS latitude and longitude columns.
    """
    # Ensure the required keys are in the config
    if "lat_col" not in config or "lon_col" not in config:
        raise KeyError("Configuration must include 'lat_col' and 'lon_col'.")

    lat_col = config["lat_col"]
    lon_col = config["lon_col"]

    # S-G filter parameters (adjust as needed)
    window_length = 51  # must be odd
    polyorder = 2

    df[f"{lat_col}_smooth_savitzky"] = savgol_filter(df[lat_col], window_length, polyorder)
    df[f"{lon_col}_smooth_savitzky"] = savgol_filter(df[lon_col], window_length, polyorder)

    return df


def data_smooth_gps_gaussian(df, config):
    """
    Smooth the GPS latitude and longitude data using a Gaussian filter.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame with GPS data.
    config : dict
        Configuration dictionary containing column names and settings.

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with smoothed GPS latitude and longitude columns.
    """
    # Ensure the required keys are in the config
    if "lat_col" not in config or "lon_col" not in config:
        raise KeyError("Configuration must include 'lat_col' and 'lon_col'.")

    lat_col = config["lat_col"]
    lon_col = config["lon_col"]

    # Gaussian filter parameter (standard deviation)
    sigma = 2

    df[f"{lat_col}_smooth_gaussian"] = gaussian_filter1d(df[lat_col], sigma)
    df[f"{lon_col}_smooth_gaussian"] = gaussian_filter1d(df[lon_col], sigma)

    return df
