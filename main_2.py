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
    compute_heading_and_yaw_rate,
    parse_time_and_compute_dt, data_filter_points_by_distance
)

from map_generator import generate_map_from_csv

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

    # Begrenze die Fenstergröße auf 90% des Bildschirms
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = int(screen_width * 0.8)
    window_height = int(screen_height * 0.8)
    root.geometry(f"{window_width}x{window_height}")

    # Hauptcontainer mit Scrollbar
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

    # Anweisungen
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

    # Scrollbare Listbox für Subsets
    listbox_frame = tk.Frame(scrollable_frame)
    listbox_frame.pack(padx=20, pady=10, fill="both", expand=True)

    listbox_scrollbar = tk.Scrollbar(listbox_frame, orient="vertical")
    subset_listbox = Listbox(listbox_frame, selectmode=MULTIPLE, font=("Arial", 12), height=15, yscrollcommand=listbox_scrollbar.set)
    listbox_scrollbar.config(command=subset_listbox.yview)

    # Füge die Listbox und Scrollbar hinzu
    subset_listbox.pack(side="left", fill="both", expand=True)
    listbox_scrollbar.pack(side="right", fill="y")

    # Lade die Dateien
    subset_files = csv_get_files_in_subfolders(subset_folder, ".csv")
    for index, subset in enumerate(subset_files):
        subset_listbox.insert(tk.END, subset)
        if pre_selected_date and subset.strip() == pre_selected_date.strip():
            subset_listbox.selection_set(index)

    # Submit Button
    tk.Button(scrollable_frame, text="Submit", command=on_submit, font=("Arial", 12)).pack(pady=10)

    # GUI starten
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
            df = data_filter_points_by_distance(
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

        # Step 10: Generate the Map
        if config.get("generate_map", True):
            generate_map_from_csv(subset_full_path)




if __name__ == "__main__":
    subset_folder = "subsets_by_date"
    default_config = {
        "create_subsets_by_date": False,
        "convert_to_planar": True,
        "calculate_distances": True,
        "parse_time": True,
        "compute_heading_yaw": True,
        "generate_map" : False,
        "statistics": True,
        "save_to_csv": True,
        "enable_statistics_on_save": True,  # Toggle this to enable/disable statistics on save
    }

    pre_selected_date = "2024-04-02.csv"
    selected_steps, selected_subsets = select_steps_and_subsets_with_gui(default_config, subset_folder, pre_selected_date)

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
        "min_distance": 2,
        "yaw_rate_given": "Gier",
        "yaw_rate_cyril": "yaw_rate",
        "time_between_points": "dt",
        **selected_steps
    }

    main(config, selected_subsets)
