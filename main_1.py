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
  7. Generating various plots
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
from csv_tools import csv_load, csv_save, csv_group_by_date_and_save, csv_get_statistics
from data_tools import (
    data_convert_to_planar,
    data_calculate_distance_iterative,
    compute_heading_and_yaw_rate,
    parse_time_and_compute_dt
)
from graph_tools import (
    graph_x_y,
    graph_x_y_with_speed_as_color,
    graph_x_y_with_yaw_rate_as_color
)


def get_files_in_subfolders(folder_path: str, file_extension: str = ".csv") -> list[str]:
    """
    Recursively searches for files with the specified extension in all subfolders.

    :param folder_path: The root folder to start searching.
    :param file_extension: The file extension to look for (e.g., '.csv').
    :return: A list of file paths relative to the root folder.
    """
    file_paths = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(file_extension):
                file_paths.append(os.path.relpath(os.path.join(root, file), folder_path))
    return file_paths


def select_steps_and_subsets_with_gui(default_config: Dict[str, bool], subset_folder: str, pre_selected_date: str = None) -> (Dict[str, bool], list[str]):
    """
    Show a GUI window for selecting which steps to run and which subsets to process.

    :param default_config: Dictionary with the default step configuration.
    :param subset_folder: Folder containing subset files to choose from.
    :param pre_selected_date: Name of the subset to pre-select (e.g., "2024-04-02.csv").
    :return: A tuple of updated step configuration and list of selected subsets.
    """
    selected_steps = default_config.copy()
    selected_subsets = []

    def on_submit():
        """
        Function to update selected steps and subsets based on user input and close the GUI window.
        """
        for key in checkboxes:
            selected_steps[key] = checkbox_vars[key].get()
        selected_subsets.extend([subset_listbox.get(i) for i in subset_listbox.curselection()])
        root.destroy()

    # Create GUI window
    root = tk.Tk()
    root.title("Select Steps and Subsets")

    # Instructions for steps
    tk.Label(root, text="Select the steps you want to run (untick to skip):", font=("Arial", 14)).pack(pady=10)

    # Create checkboxes for each step
    checkbox_vars = {}
    checkboxes = {}
    for key, value in default_config.items():
        var = tk.BooleanVar(value=value)
        checkbox_vars[key] = var
        cb = tk.Checkbutton(root, text=key.replace("_", " ").capitalize(), variable=var, font=("Arial", 12))
        cb.pack(anchor="w", padx=20)
        checkboxes[key] = cb

    # Divider
    tk.Label(root, text="Select subsets to process:", font=("Arial", 14)).pack(pady=10)

    # Listbox for subsets
    subset_listbox = Listbox(root, selectmode=MULTIPLE, font=("Arial", 12), height=28, width=50)

    # Recursively get CSV files in subfolders
    subset_files = get_files_in_subfolders(subset_folder, ".csv")

    # Insert files and pre-select the preferred subset if available
    for index, subset in enumerate(subset_files):
        subset_listbox.insert(tk.END, subset)
        # Match the pre-selected date (ensure exact match)
        if pre_selected_date and subset.strip() == pre_selected_date.strip():
            subset_listbox.selection_set(index)

    subset_listbox.pack(padx=20, pady=10)

    # Submit button
    tk.Button(root, text="Submit", command=on_submit, font=("Arial", 12)).pack(pady=10)

    # Run the GUI event loop
    root.mainloop()
    return selected_steps, selected_subsets


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

    root = tk.Tk()
    root.withdraw()  # Hide the root Tkinter window (optional)


    # Process each subset file
    for subset_file in subsets:
        subset_full_path = os.path.join(config["output_folder_for_subsets_by_date"], subset_file)
        print(f"Processing subset: {subset_full_path}")
        df = csv_load(subset_full_path)
        if df.empty:
            print(f"The subset '{subset_file}' is empty. Skipping.")
            continue

        # Step 3: Convert to planar coordinates
        if config.get("convert_to_planar", True):
            df = data_convert_to_planar(df, config["lat_col"], config["lon_col"])

        # Step 4: Calculate distances
        if config.get("calculate_distances", True):
            df = data_calculate_distance_iterative(
                df, x_col=config["x_col"], y_col=config["y_col"], min_distance=config["min_distance"]
            )

        # Step 5: Parse time and compute time differences
        if config.get("parse_time", True):
            df = parse_time_and_compute_dt(df, config["date_column"])

        # Step 6: Compute heading and yaw rate
        if config.get("compute_heading_yaw", True):
            df = compute_heading_and_yaw_rate(
                df, config["x_col"], config["y_col"], dt=config["time_between_points"]
            )

        # Step 7: Generate plots
        if config.get("generate_plots", True):
            graph_x_y(df, config["x_col"], config["y_col"], config["min_distance"])
            graph_x_y_with_speed_as_color(df, config["x_col"], config["y_col"], config["speed_column"], config["min_distance"])
            graph_x_y_with_yaw_rate_as_color(df, config["x_col"], config["y_col"], config["yaw_rate_cyril"], config["min_distance"])

        # Step 8: Save processed data
        if config.get("save_to_csv", True):
            # Resolve the full path of the input file
            full_subset_file_path = os.path.join(config["output_folder_for_subsets_by_date"], subset_file)

            # Extract the folder where the input file resides
            input_folder = os.path.dirname(full_subset_file_path)

            # Construct the base output file path
            processed_filename = f"{os.path.basename(subset_file).split('.')[0]}.csv"
            toggled_suffixes = []
            if config.get("convert_to_planar"):
                toggled_suffixes.append("planar")
            if config.get("calculate_distances"):
                toggled_suffixes.append("dist")
            if config.get("parse_time"):
                toggled_suffixes.append("time")
            if config.get("compute_heading_yaw"):
                toggled_suffixes.append("yaw")

            # Add the suffixes to the filename
            if toggled_suffixes:
                processed_filename = f"{processed_filename.split('.')[0]}_{'_'.join(toggled_suffixes)}.csv"

            date_specific_output = os.path.join(input_folder, processed_filename)

            # Save the processed file and optionally calculate statistics
            csv_save(
                df,
                date_specific_output,
                ensure_folder=False,
                suffixes=toggled_suffixes,
                run_stats=config.get("enable_statistics_on_save", False)
            )
            print(f"Saved processed data to {date_specific_output}")

        # Step 9: Statistics
        if config.get("statistics", True):
            print(f"Saving statistics for {subset_full_path}...")
            csv_get_statistics(subset_full_path)



if __name__ == "__main__":
    subset_folder = "subsets_by_date"
    default_config = {
        "create_subsets_by_date": False,
        "convert_to_planar": True,
        "calculate_distances": True,
        "parse_time": True,
        "compute_heading_yaw": True,
        "generate_plots": True,
        "statistics": True,
        "save_to_csv": True,
        "enable_statistics_on_save": True,  # Toggle this to enable/disable statistics on save
    }

    pre_selected_date = "2024-04-02.csv"
    selected_steps, selected_subsets = select_steps_and_subsets_with_gui(default_config, subset_folder, pre_selected_date)

    config = {
        "input_file": "BR203_Fruehling.csv",
        "output_folder_for_subsets_by_date": subset_folder,
        "date_column": "DatumZeit",
        "speed_column": "Geschwindigkeit in m/s",
        "lat_col": "GPS_lat",
        "lon_col": "GPS_lon",
        "x_col": "x",
        "y_col": "y",
        "distance_col": "distance",
        "min_distance": 1,
        "yaw_rate_given": "Gier",
        "yaw_rate_cyril": "yaw_rate",
        "time_between_points": "dt",
        **selected_steps
    }

    main(config, selected_subsets)
