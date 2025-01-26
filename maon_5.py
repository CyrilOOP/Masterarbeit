"""
Script Name: data_processing.py

Description:
  This script provides a complete workflow for processing GPS data from a CSV file, including:
  1. Loading CSV data
  2. Filtering rows by a target date
  3. Converting GPS coordinates (lat/lon) to planar (x, y)
  4. Calculating distances between consecutive points
  5. Parsing timestamps and computing dt
  6. Calculating heading & yaw rate
  7. Saving the resulting DataFrame to a date-specific CSV file

Requirements:
  - csv_tools.py
    * csv_load
    * csv_save
    * csv_group_by_date_and_save
    * csv_get_statistics
    * csv_get_files_in_subfolders

  - data_tools.py
    * data_convert_to_planar
    * data_compute_heading_and_yaw_rate
    * parse_time_and_compute_dt
    * data_filter_points_by_distance
    * data_compute_heading_and_yaw_rate_spline

  - map_generator.py
    * generate_map_from_csv

Usage Example:
    python data_processing.py

Author:
  Cyril Piette / TU_Berlin / 2025
"""

import os
import tkinter as tk
from tkinter import Listbox, MULTIPLE
from typing import Dict, Any, List, Tuple

# Local module imports
from csv_tools import (
    csv_load,
    csv_save,
    csv_group_by_date_and_save,
    csv_get_statistics,
    csv_get_files_in_subfolders,
)
from data_tools import (
    data_convert_to_planar,
    data_compute_heading_from_xy,
    parse_time_and_compute_dt,
    data_filter_points_by_distance,
    data_compute_yaw_rate_from_heading,
    data_smooth_gps_savitzky, data_smooth_gps_gaussian,
)
from map_generator import generate_map_from_csv


def select_steps_and_subsets_with_gui(
    default_config: Dict[str, bool],
    subset_folder: str,
    pre_selected_date: str = None
) -> Tuple[Dict[str, bool], List[str], float]:
    """
    Shows a compact GUI for selecting which steps to run, which subsets to process,
    and setting a minimum distance threshold.

    Parameters
    ----------
    default_config : Dict[str, bool]
        Dictionary with the default step configuration (step_name -> bool).
    subset_folder : str
        Path to the folder containing CSV subset files.
    pre_selected_date : str, optional
        Name of the subset file to pre-select in the list (e.g., "2024-04-02.csv").

    Returns
    -------
    Tuple[Dict[str, bool], List[str], float]
        - Updated step configuration (which steps are enabled/disabled).
        - List of subset file paths selected in the GUI (relative to subset_folder).
        - The min_distance value (float).
    """

    root = tk.Tk()
    root.title("Data Processing Options")

    # --- Steps to Run (Checkbuttons) ---
    steps_frame = tk.LabelFrame(root, text="Steps to Run", padx=10, pady=10)
    steps_frame.pack(padx=10, pady=5, fill="x")

    checkbox_vars = {}
    for step_name, enabled_by_default in default_config.items():
        var = tk.BooleanVar(value=enabled_by_default)
        checkbox_vars[step_name] = var
        checkbutton = tk.Checkbutton(
            steps_frame,
            text=step_name.replace("_", " ").capitalize(),
            variable=var
        )
        checkbutton.pack(anchor="w")

    # --- Subsets to Process (Listbox) ---
    subsets_frame = tk.LabelFrame(root, text="Subsets to Process", padx=10, pady=10)
    subsets_frame.pack(padx=10, pady=5, fill="both", expand=True)

    list_scrollbar = tk.Scrollbar(subsets_frame, orient="vertical")
    list_scrollbar.pack(side="right", fill="y")

    subset_listbox = Listbox(
        subsets_frame,
        selectmode=MULTIPLE,
        yscrollcommand=list_scrollbar.set,
        height=8  # Adjust as needed
    )
    subset_listbox.pack(side="left", fill="both", expand=True)
    list_scrollbar.config(command=subset_listbox.yview)

    # Load subset files (relative paths)
    subset_files = csv_get_files_in_subfolders(subset_folder, ".csv")

    # We will store the original relative paths here
    # but display only the base name in the listbox for clarity
    file_paths = []  # keeps the relative paths
    for index, relative_path in enumerate(subset_files):
        # Extract just the filename from the relative path
        file_name = os.path.basename(relative_path)

        file_paths.append(relative_path)  # keep the original relative path
        subset_listbox.insert(tk.END, file_name)

        # Pre-select if it matches the base filename
        if pre_selected_date and file_name.strip() == pre_selected_date.strip():
            subset_listbox.selection_set(index)

    # --- Minimum Distance Input ---
    distance_frame = tk.Frame(root)
    distance_frame.pack(padx=10, pady=5, fill="x")

    tk.Label(distance_frame, text="Minimum Distance (meters):").pack(side="left")

    min_distance_value = tk.DoubleVar(value=1.0)
    tk.Entry(distance_frame, textvariable=min_distance_value, width=10).pack(side="left", padx=5)

    # --- Submit Button ---
    def on_submit():
        # Update step config
        updated_config = {k: v.get() for k, v in checkbox_vars.items()}

        # Gather the **relative paths** of the selected files
        selected_indices = subset_listbox.curselection()
        selected_subset_list = [file_paths[i] for i in selected_indices]

        # Fetch the user-selected min distance
        user_min_distance = min_distance_value.get()

        # Store in outer scope
        nonlocal selected_steps, selected_subsets, min_distance
        selected_steps = updated_config
        selected_subsets = selected_subset_list
        min_distance = user_min_distance

        root.destroy()

    tk.Button(root, text="Submit", command=on_submit).pack(pady=10)

    # Let Tkinter calculate optimal size
    root.update_idletasks()
    root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())

    # Variables to hold selected values
    selected_steps, selected_subsets, min_distance = {}, [], 1.0

    # Run the event loop
    root.mainloop()

    return selected_steps, selected_subsets, min_distance


def main(config: Dict[str, Any], subsets: List[str]) -> None:
    """
    Main entry point for the data processing workflow.

    Parameters
    ----------
    config : Dict[str, Any]
        Dictionary containing configuration options, e.g.:
          - "input_file": path to the CSV file
          - "output_folder_for_subsets_by_date": folder for creating subsets
          - "date_column": the name of the date/time column in the CSV
          - "lat_col", "lon_col": column names for GPS lat/lon
          - "x_col", "y_col": column names for planar coords
          - "time_between_points": label for dt column
          - "min_distance": minimum distance to keep
          - Additional booleans for toggling each step.

    subsets : List[str]
        List of subset file **relative paths** to process (relative to config["output_folder_for_subsets_by_date"]).
    """

    # 1. Group by date and save subsets
    if config.get("create_subsets_by_date"):
        print("Grouping CSV data by date and saving subsets...")
        df = csv_load(config)
        if df.empty:
            print("The input CSV file is empty. Exiting.")
            return
        csv_group_by_date_and_save(df, config["output_folder_for_subsets_by_date"], column_name=config["date_column"])
        print("Grouping by date completed.")

    # 2. Process each subset file
    for subset_file in subsets:
        # subset_file is a *relative path* from the chosen folder
        subset_full_path = os.path.join(config["output_folder_for_subsets_by_date"], subset_file)
        print(f"\nProcessing subset: {subset_full_path}")

        df_subset = csv_load(subset_full_path)
        processed_suffixes = []

        if df_subset.empty:
            print(f"Subset '{subset_file}' is empty. Skipping.")
            continue

        # Smoothing the GPS coordinates with Savitzky
        if config.get("smooth_gps_data_with_savitzky", True):
            df_subset = data_smooth_gps_savitzky(df_subset, config)
            processed_suffixes.append("savitzky")

        # Smoothing the GPS coordinates with Gaussian
        if config.get("smooth_gps_data_with_gaussian", True):
            df_subset = data_smooth_gps_gaussian(df_subset, config)
            processed_suffixes.append("gaussian")

        # Convert to planar coordinates
        if config.get("convert_to_planar", True):
            df_subset = data_convert_to_planar(df_subset, config)
            processed_suffixes.append("planar")

        # Filter points based on minimum distance
        if config.get("filter_with_distances", True):
            df_subset = data_filter_points_by_distance(df_subset, config)
            processed_suffixes.append("dist")

        # Parse time and compute dt
        if config.get("parse_time", True):
            df_subset = parse_time_and_compute_dt(df_subset, config["date_column"])
            processed_suffixes.append("time")

        # Compute heading from xy
        if config.get("compute_heading_from_xy", True):
            df_subset = data_compute_heading_from_xy(
                df_subset,
                x_col=config["x_col"],
                y_col=config["y_col"],
                heading_col="heading_deg"
            )
            processed_suffixes.append("heading")

        # Compute the yaw rate from the heading
        if config.get("compute_yaw_rate_from_heading", True):
            df_subset = data_compute_yaw_rate_from_heading(
                df_subset,
                heading_col="heading_deg",  # or whatever you call it
                dt_col="dt",
                yaw_rate_col="yaw_rate_deg_s"
            )
            processed_suffixes.append("yawRate")

        # Save processed data to CSV
        if config.get("save_to_csv", True):
            suffix_string = "_".join(processed_suffixes)
            base_filename = os.path.splitext(subset_file)[0]
            processed_filename = f"{base_filename}_{suffix_string}.csv"
            save_path = os.path.join(config["output_folder_for_subsets_by_date"], processed_filename)

            csv_save(
                df_subset,
                save_path,
                ensure_folder=False,
                #suffixes=list(processed_suffixes),
                run_stats=config.get("enable_statistics_on_save", False)
            )

        # Generate statistics
        if config.get("statistics", False):
            print(f"Saving statistics for: {subset_full_path}")
            csv_get_statistics(subset_full_path)

        # Generate the map based on the toggles
        if config.get("generate_map", False):  # Check if map generation is enabled in the configuration
            if config.get("save_to_csv", True):  # If save_to_csv is enabled, use the processed CSV file for the map
                print(f"Generating map using the processed file: {save_path}")
                generate_map_from_csv(save_path)
            else:  # If save_to_csv is disabled, use the original subset file for the map
                print(f"Generating map using the original subset file: {subset_full_path}")
                generate_map_from_csv(subset_full_path)


if __name__ == "__main__":
    # Path where the subsets are expected to be stored
    SUBSET_FOLDER = "subsets_by_date"

    # Default configuration
    default_config = {
        "create_subsets_by_date": False,
        "statistics": False,
        "smooth_gps_data_savitzky" : True,
        "smooth_gps_data_gaussian": True,
        "convert_to_planar": True,
        "filter_with_distances": True,
        "parse_time": True,
        "compute_heading_from_xy": True,
        "compute_yaw_rate_from_heading": True,
        "generate_map": False,
        "save_to_csv": True,
        "enable_statistics_on_save": True,
    }

    # Optionally, specify a file in subsets_by_date to pre-select
    pre_selected_date = "2024-04-02.csv"

    # Launch the compact GUI
    selected_steps, selected_subsets, min_distance = select_steps_and_subsets_with_gui(
        default_config,
        SUBSET_FOLDER,
        pre_selected_date
    )

    # Merge selected steps into final config
    config = {
        "input_file_path": None,  # or specify an actual path if needed
        "output_folder_for_subsets_by_date": SUBSET_FOLDER,
        "date_column": "DatumZeit",
        "speed_column": "Geschwindigkeit in m/s",
        "lat_col": "GPS_lat",
        "lon_col": "GPS_lon",
        "x_col": "x",
        "y_col": "y",
        "lat_col_smooth": "GPS_lat_smooth",
        "lon_col_smooth": "GPS_lon_smooth",
        "distance_col": "distance",
        "time_between_points": "dt",
        "min_distance": min_distance,
        **selected_steps
    }

    # Run the main data processing workflow
    main(config, selected_subsets)
