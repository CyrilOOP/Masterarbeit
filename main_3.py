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

  8. Saving the resulting DataFrame to a date-specific CSV file

Requirements:
  - csv_tools.py with functions: csv_load, csv_save, csv_filter_by_day, csv_group_by_date_and_save
  - data_tools.py with functions: data_convert_to_planar, data_calculate_distance_iterative,
    compute_heading_and_yaw_rate, parse_time_and_compute_dt
  - graph_tools.py with functions: graph_x_y, graph_x_y_with_speed_as_color, graph_x_y_with_yaw_rate_as_color

Usage Example:
    python data_processing.py

Author:
  Cyril Piette / TU_Berlin / 2025
"""

from typing import Dict, Any
import os
import tkinter as tk
from tkinter import Listbox, MULTIPLE
from csv_tools import csv_load, csv_save, csv_group_by_date_and_save, csv_get_statistics, csv_get_files_in_subfolders
from data_tools import (
    data_convert_to_planar,
    data_compute_heading_and_yaw_rate,
    parse_time_and_compute_dt, data_filter_points_by_distance, data_compute_heading_and_yaw_rate_spline,
   )

from map_generator import generate_map_from_csv

def select_steps_and_subsets_with_gui(default_config: Dict[str, bool], subset_folder: str, pre_selected_date: str = None) -> (Dict[str, bool], list[str], float):
    """
    Show a GUI window for selecting which steps to run and which subsets to process.

    :param default_config: Dictionary with the default step configuration.
    :param subset_folder: Folder containing subset files to choose from.
    :param pre_selected_date: Name of the subset to pre-select (e.g., "2024-04-02.csv").
    :return: A tuple of updated step configuration, list of selected subsets, and min_distance value.
    """
    selected_steps = default_config.copy()
    selected_subsets = []

    # Create GUI window
    root = tk.Tk()
    root.title("Select Steps and Subsets")

    # Initialize min_distance variable after root creation
    min_distance_value = tk.DoubleVar(value=1.0)  # Default value is 1.0

    def on_submit():
        """
        Function to update selected steps and subsets based on user input and close the GUI window.
        """
        for key in checkboxes:
            selected_steps[key] = checkbox_vars[key].get()
        selected_subsets.extend([subset_listbox.get(i) for i in subset_listbox.curselection()])
        root.destroy()

    # Limit window size to 90% of screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = int(screen_width * 0.8)
    window_height = int(screen_height * 0.8)
    root.geometry(f"{window_width}x{window_height}")

    # Main container with scrollbar
    main_frame = tk.Frame(root)
    main_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(main_frame)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Instructions
    tk.Label(scrollable_frame, text="Select the steps you want to run (untick to skip):", font=("Arial", 14)).pack(pady=10)

    # Create checkboxes for each step
    checkbox_vars = {}
    checkboxes = {}
    for key, value in default_config.items():
        var = tk.BooleanVar(value=value)
        checkbox_vars[key] = var
        cb = tk.Checkbutton(scrollable_frame, text=key.replace("_", " ").capitalize(), variable=var, font=("Arial", 12))
        cb.pack(anchor="w", padx=20)
        checkboxes[key] = cb

    # Divider
    tk.Label(scrollable_frame, text="Select subsets to process:", font=("Arial", 14)).pack(pady=10)

    # Scrollable Listbox for subsets
    listbox_frame = tk.Frame(scrollable_frame)
    listbox_frame.pack(padx=20, pady=10, fill="both", expand=True)

    listbox_scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
    subset_listbox = Listbox(listbox_frame, selectmode=MULTIPLE, font=("Arial", 12), height=15, yscrollcommand=listbox_scrollbar.set)
    listbox_scrollbar.config(command=subset_listbox.yview)

    # Add the Listbox and Scrollbar
    subset_listbox.pack(side="left", fill="both", expand=True)
    listbox_scrollbar.pack(side="right", fill="y")

    # Load files
    subset_files = csv_get_files_in_subfolders(subset_folder, ".csv")
    for index, subset in enumerate(subset_files):
        subset_listbox.insert(tk.END, subset)
        if pre_selected_date and subset.strip() == pre_selected_date.strip():
            subset_listbox.selection_set(index)

    # Add input for min_distance
    tk.Label(scrollable_frame, text="Set Minimum Distance (meters):", font=("Arial", 14)).pack(pady=10)
    min_distance_entry = tk.Entry(scrollable_frame, font=("Arial", 12), textvariable=min_distance_value)
    min_distance_entry.pack(padx=20, pady=5)

    # Submit Button
    tk.Button(scrollable_frame, text="Submit", command=on_submit, font=("Arial", 12)).pack(pady=10)

    # Start the GUI
    root.mainloop()
    return selected_steps, selected_subsets, min_distance_value.get()






def main(config: Dict[str, Any], subsets: list[str]) -> None:
    """
    Main entry point for the data processing workflow.

    :param config: Dictionary containing configuration options, e.g.:
        - "input_file": path to the CSV file
        - "output_folder_for_subsets_by_date": folder for creating subsets
        - Flags for toggling steps
    :param subsets: List of subset files to process.
    :return: None
    """



    # If enabled, group by date and save before processing subsets
    if config.get("create_subsets_by_date", True):
        print("Grouping CSV data by date and saving subsets...")
        df = csv_load(config["input_file"])
        if df.empty:
            print("The input CSV file is empty. Exiting.")
            return
        csv_group_by_date_and_save(df, config["output_folder_for_subsets_by_date"], column_name=config["date_column"])
        print("Grouping by date completed.")


    # Process each subset file
    for subset_file in subsets:
        subset_full_path = os.path.join(config["output_folder_for_subsets_by_date"], subset_file)
        print(f"Processing subset: {subset_full_path}")
        df = csv_load(subset_full_path)
        processed_suffixes = set()
        print(f"The suffixe is '{processed_suffixes}' .")
        if df.empty:
            print(f"The subset '{subset_file}' is empty. Skipping.")
            continue

        # Convert to planar coordinates
        if config.get("convert_to_planar", True):
            df = data_convert_to_planar(df, config["lat_col"], config["lon_col"])
            processed_suffixes.add("planar")
            print(f"The suffixe is '{processed_suffixes}' .")


        # Calculate distances
        if config.get("filter_with_distances", True):
            df = data_filter_points_by_distance(
                df, x_col=config["x_col"], y_col=config["y_col"], min_distance=config["min_distance"]
            )
            processed_suffixes.add("dist")
            print(f"The suffixe is '{processed_suffixes}' .")

        # Parse time and compute time differences
        if config.get("parse_time", True):
            df = parse_time_and_compute_dt(df, config["date_column"])
            processed_suffixes.add("time")
            print(f"The suffixe is '{processed_suffixes}' .")

        # Compute heading and yaw rate
        if config.get("compute_heading_yaw", True):
            df = compute_heading_and_yaw_rate(
                df, config["x_col"], config["y_col"], dt=config["time_between_points"]
            )
            processed_suffixes.add("yaw")
            print(f"The suffixe is '{processed_suffixes}' .")

        # Compute Heading and Yaw rate with spline
        if config.get("compute_heading_and_yaw_rate_with spline", True):
            df = data_compute_heading_and_yaw_rate(
                df=df,
                x_col=config["x_col"],
                y_col=config["y_col"],
                dt=config["time_between_points"]
            )
            processed_suffixes.add("spline")


        # Save processed data
        if config.get("save_to_csv", True):

            # Generate the final filename with unique suffixes
            print(f"The suffixe is '{processed_suffixes}' .")
            suffix_string = "_".join(sorted(processed_suffixes))  # Sort for consistency
            base_filename = os.path.splitext(subset_file)[0]  # Extract base name
            processed_filename = f"{base_filename}_{suffix_string}.csv"  # Build the filename

            # Save the processed file
            save_path = os.path.join(config["output_folder_for_subsets_by_date"], processed_filename)
            csv_save(
                df,
                save_path,
                ensure_folder=False,
                suffixes=list(processed_suffixes),
                run_stats=config.get("enable_statistics_on_save", True)
            )
            print(f"Saved processed data to {save_path}")


        # Statistics
        if config.get("statistics", True):
            print(f"Saving statistics for {subset_full_path}...")
            csv_get_statistics(subset_full_path)

        # Generate the Map
        if config.get("generate_map", True):
            generate_map_from_csv(subset_full_path)




if __name__ == "__main__":
    subset_folder = "subsets_by_date"
    default_config = {
        "create_subsets_by_date": False,
        "convert_to_planar": True,
        "filter_with_distances": True,
        "parse_time": True,
        "compute_heading_yaw": True,
        "generate_map" : False,
        "statistics": False,
        "compute_heading_and_yaw_rate_with spline" : True,
        "save_to_csv": True,
        "enable_statistics_on_save": True,  # Toggle this to enable/disable statistics on save
    }

    pre_selected_date = "2024-04-02.csv"
    selected_steps, selected_subsets, min_distance = select_steps_and_subsets_with_gui(default_config, subset_folder,
                                                                                       pre_selected_date)

    config = {
        "input_file": None,  # Allow dynamic file selection
        "output_folder_for_subsets_by_date": subset_folder,
        "date_column": "DatumZeit",
        "speed_column": "Geschwindigkeit in m/s",
        "lat_col": "GPS_lat",
        "lon_col": "GPS_lon",
        "x_col": "x",
        "y_col": "y",
        "distance_col": "distance",
        "min_distance": min_distance,  # Use the value from the GUI
        "yaw_rate_given": "Gier",
        "yaw_rate_cyril": "yaw_rate",
        "time_between_points": "dt",
        "save_to_csv": True,
        **selected_steps
    }

    main(config, selected_subsets)
