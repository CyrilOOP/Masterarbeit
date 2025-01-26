import pandas as pd
import os
from typing import List
from tkinter import Tk, filedialog
"""
Module: CSV Tools
Description: Contains utilities for loading, saving, and manipulating CSV files, as well as datetime statistics.
"""

def csv_load(file_path=None):
    """
    Load a CSV file into a pandas DataFrame.
    If no file_path is provided, open a file dialog to allow the user to browse for a file.

    Args:
        file_path: Path to the CSV file. If None, a file dialog will be shown.

    Returns:
        A pandas DataFrame containing the CSV data.

    Raises:
        FileNotFoundError: If no file is selected or the provided path does not exist.
    """
    # If file path is not provided, open file dialog
    if file_path is None:
        root = Tk()
        root.withdraw()  # Hide the root Tkinter window
        file_path = filedialog.askopenfilename(
            title="Select a CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:  # No file selected
            raise FileNotFoundError("No file selected. Operation cancelled.")

    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    # Load the CSV file into a DataFrame
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    return df.copy()


def csv_save(df, file_path, ensure_folder=False, run_stats=False):
    """
    Save a pandas DataFrame to a CSV file without modifying the file path.

    Args:
        df: The DataFrame to save.
        file_path: The complete file path, including suffixes and extension.
        ensure_folder: Whether to automatically create the folder structure.
        run_stats: Whether to calculate statistics for the saved file.
    """

    if ensure_folder:
        # Ensure the parent directory exists
        parent_dir = os.path.dirname(file_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            print(f"Created directory: {parent_dir}")

    # Save the DataFrame
    df.to_csv(file_path, index=False)
    print(f"File saved to: {file_path}")

    # Optionally calculate statistics
    if run_stats:
        csv_get_statistics(file_path)

def csv_get_files_in_subfolders(folder_path: str, file_extension: str = ".csv") -> List[str]:
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

def csv_drop_na(df, *columns):
    """
    Remove rows with NA values in the specified columns.
    If no columns are specified, remove rows with NA in any column.
    """
    if columns:
        return df.dropna(subset=columns)
    else:
        return df.dropna()

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
    Generate and save enhanced statistics for a CSV file, including missing, zero value analysis,
    and specific datetime analysis, to a text file.

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

    # Add statistics for DatumZeit column
    if 'DatumZeit' in df.columns:
        stats_report.append("=== DatumZeit Column Analysis ===\n")
        try:
            df['DatumZeit'] = pd.to_datetime(df['DatumZeit'], errors='coerce')  # Parse as datetime
            if df['DatumZeit'].isnull().all():
                stats_report.append("Failed to parse DatumZeit column as datetime.\n\n")
            else:
                stats_report.append(f"Total non-null datetime entries: {df['DatumZeit'].notnull().sum()}\n")
                stats_report.append(f"Earliest timestamp: {df['DatumZeit'].min()}\n")
                stats_report.append(f"Latest timestamp: {df['DatumZeit'].max()}\n")
                stats_report.append("Entries per day:\n")
                stats_report.append(df['DatumZeit'].dt.date.value_counts().to_string() + "\n\n")
        except Exception as e:
            stats_report.append(f"Error processing DatumZeit column: {e}\n\n")
    else:
        stats_report.append("DatumZeit column not found.\n\n")

    # Save statistics to a text file
    output_file = f"{os.path.splitext(file_path)[0]}_statistics.txt"
    try:
        with open(output_file, "w", encoding=encoding) as f:  # Specify encoding here
            f.write("".join(stats_report))
        print(f"Statistics saved to {output_file}")
    except Exception as e:
        print(f"Error writing statistics to file: {e}")




