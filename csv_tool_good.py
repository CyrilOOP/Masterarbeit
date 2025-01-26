import pandas as pd
from datetime import datetime
import os
import tkinter as tk
from tkinter import scrolledtext
import threading

"""
Module: CSV Tools
Description: Contains utilities for loading, saving, and manipulating CSV files, as well as datetime statistics.
"""

def csv_load(file_path):
    """
    Load a CSV file into a pandas DataFrame.
    """
    df = pd.read_csv(file_path)
    return df.copy()


def csv_save(df, file_path, ensure_folder=False, suffixes=None, run_stats=False):
    """
    Save a pandas DataFrame to a CSV file with dynamic suffix support and optional statistics.

    Args:
        df: The DataFrame to save.
        file_path: The full path to save the CSV file, including the base file name.
        ensure_folder: Whether to automatically create the folder structure.
        suffixes: A list of suffixes (e.g., ["planar", "dist", "time", "yaw"]) to append to the file name.
        run_stats: Whether to calculate statistics for the saved file.
    """
    if ensure_folder:
        # Ensure the parent directory exists
        parent_dir = os.path.dirname(file_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            print(f"Created directory: {parent_dir}")

    # Add suffixes to the file name if provided
    if suffixes:
        suffix_string = "_".join(suffixes)  # Combine suffixes with underscores
        file_name, file_ext = os.path.splitext(file_path)
        file_path = f"{file_name}_{suffix_string}{file_ext}"

    # Save the DataFrame
    df.to_csv(file_path, index=False)
    print(f"File saved to: {file_path}")

    # Optionally calculate statistics
    if run_stats:
        from csv_tools import csv_get_statistics  # Import inside function to avoid circular dependencies
        csv_get_statistics(file_path)
        print(f"Statistics calculated for: {file_path}")




def csv_drop_na(df, *columns):
    """
    Remove rows with NA values in the specified columns.
    If no columns are specified, remove rows with NA in any column.
    """
    if columns:
        return df.dropna(subset=columns)
    else:
        return df.dropna()

def csv_get_datetime_stats(df, column_name="DatumZeit"):
    """
    Print statistics about a datetime column, including the earliest, latest, range of dates,
    and the number of rows in the DataFrame.
    Raise a ValueError if the column does not exist.
    """
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")

    df[column_name] = pd.to_datetime(df[column_name])  # Ensure datetime format

    # Calculate the statistics
    earliest = df[column_name].min()
    latest = df[column_name].max()
    date_range = latest - earliest
    num_rows = len(df)  # Get the number of rows

    # Print the statistics to the console
    print(f"Number of rows: {num_rows}")
    print(f"Earliest Date: {earliest}")
    print(f"Latest Date: {latest}")
    print(f"Date Range: {date_range}")

def csv_get_lat_long_stats(df, lat_column, long_column):
    """
    Return statistics about latitude and longitude columns, including the min, max, and range of values.
    Raise a ValueError if the columns do not exist.
    """
    if lat_column not in df.columns or long_column not in df.columns:
        raise ValueError(f"Columns '{lat_column}' or '{long_column}' do not exist in the DataFrame.")

    # Latitude statistics
    lat_min = df[lat_column].min()
    lat_max = df[lat_column].max()
    lat_range = lat_max - lat_min

    # Longitude statistics
    long_min = df[long_column].min()
    long_max = df[long_column].max()
    long_range = long_max - long_min

    # Print statistics to the console
    print("Latitude Statistics:")
    print(f"  Minimum: {lat_min}")
    print(f"  Maximum: {lat_max}")
    print(f"  Range: {lat_range}")

    print("\nLongitude Statistics:")
    print(f"  Minimum: {long_min}")
    print(f"  Maximum: {long_max}")
    print(f"  Range: {long_range}")

    # Return stats as a dictionary
    return {
        "latitude": {"min": lat_min, "max": lat_max, "range": lat_range},
        "longitude": {"min": long_min, "max": long_max, "range": long_range}
    }

def csv_filter_by_day(df, column_name, target_date):
    """
    Keep only rows where the date matches the target date.
    Raise a ValueError if no matching rows are found.
    """
    df[column_name] = pd.to_datetime(df[column_name])  # Ensure datetime format
    filtered_df = df[df[column_name].dt.date == datetime.strptime(target_date, '%Y-%m-%d').date()]
    if filtered_df.empty:
        raise ValueError(f"No rows found for the date '{target_date}'.")
    return filtered_df

def csv_filter_by_datetime_range(df, column_name, start_datetime, end_datetime):
    """
    Keep only rows where the datetime is within the specified range.
    Raise a ValueError if no matching rows are found.
    """
    df[column_name] = pd.to_datetime(df[column_name])  # Ensure datetime format
    start_datetime = pd.to_datetime(start_datetime)
    end_datetime = pd.to_datetime(end_datetime)
    filtered_df = df[(df[column_name] >= start_datetime) & (df[column_name] <= end_datetime)]
    if filtered_df.empty:
        raise ValueError(f"No rows found in the range {start_datetime} to {end_datetime}.")
    return filtered_df

def csv_group_by_date_and_save(df, output_folder, column_name="DatumZeit"):
    """
    Groups the DataFrame by the date part of a datetime column, creates a subfolder for each date,
    and saves the corresponding data into a CSV file inside that subfolder.
    If a file already exists, it will be deleted with a notification.

    Args:
        df: pandas DataFrame containing the data.
        output_folder: The folder where the output subfolders and CSV files will be stored.
        column_name: The name of the column to group by (should be a datetime column).
    """
    # Ensure the column is in datetime format
    df[column_name] = pd.to_datetime(df[column_name])

    # Group by the date part of the datetime column
    grouped = df.groupby(df[column_name].dt.date)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Save each group to a separate CSV file in its own subfolder
    for date, group in grouped:
        date_str = date.strftime('%Y-%m-%d')  # Format date as string for folder and filename
        date_folder_path = os.path.join(output_folder, date_str)

        # Create a subfolder for the date if it doesn't exist
        if not os.path.exists(date_folder_path):
            os.makedirs(date_folder_path)

        group_file_path = os.path.join(date_folder_path, f"{date_str}.csv")

        # Check if file already exists and delete it
        if os.path.exists(group_file_path):
            os.remove(group_file_path)
            print(f"Existing file '{group_file_path}' deleted.")

        # Save the new file
        group.to_csv(group_file_path, index=False)
        print(f"Saved data for {date_str} to {group_file_path}")


def csv_get_statistics(file_path, encoding="utf-8"):
    """
    Generate and save enhanced statistics for a CSV file, including missing and zero value analysis, to a text file.

    Args:
        file_path: Path to the CSV file.
        encoding: Encoding to use when saving the text file. Default is 'utf-8'.

    Returns:
        None
    """
    # Load the CSV file
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return

    # Initialize the stats report
    stats_report = [f"=== CSV File Statistics ===\n"]
    stats_report.append(f"File: {file_path}\n")
    stats_report.append(f"Number of Rows: {df.shape[0]}\n")
    stats_report.append(f"Number of Columns: {df.shape[1]}\n\n")

    # Add column types
    stats_report.append("=== Column Data Types ===\n")
    stats_report.append(df.dtypes.to_string() + "\n\n")

    # Add missing and zero value counts
    stats_report.append("=== Missing and Zero Value Analysis ===\n")
    missing_values = df.isnull().sum()
    zero_values = (df == 0).sum(numeric_only=True)
    combined_stats = pd.DataFrame({"Missing Values": missing_values, "Zero Values": zero_values})
    stats_report.append(combined_stats.to_string() + "\n\n")

    # Add statistics for numerical columns
    stats_report.append("=== Numerical Column Statistics ===\n")
    if not df.select_dtypes(include=["number"]).empty:
        stats_report.append(df.describe().to_string() + "\n\n")
    else:
        stats_report.append("No numerical columns found.\n\n")

    # Add statistics for categorical columns
    stats_report.append("=== Categorical Column Analysis ===\n")
    categorical_columns = df.select_dtypes(include=["object"])
    if not categorical_columns.empty:
        for col in categorical_columns.columns:
            stats_report.append(f"Top Values in '{col}':\n")
            stats_report.append(categorical_columns[col].value_counts().head(5).to_string() + "\n\n")
    else:
        stats_report.append("No categorical columns found.\n\n")

    # Save statistics to a text file
    output_file = f"{os.path.splitext(file_path)[0]}_statistics.txt"
    try:
        with open(output_file, "w", encoding=encoding) as f:  # Specify encoding here
            f.write("".join(stats_report))
        print(f"Statistics saved to {output_file}")
    except Exception as e:
        print(f"Error writing statistics to file: {e}")





def main():
    """
    Quick testing for any function.
    """
    # Example: Testing csv_load
    print("Testing csv_load function...")
    file_path = input("Enter the CSV file path to load: ")
    df = csv_load(file_path)
    print("Loaded DataFrame:")
    print(df.head())

    # stats
    print("\nStats function...")
    csv_get_datetime_stats(df)

if __name__ == "__main__":
    main()

