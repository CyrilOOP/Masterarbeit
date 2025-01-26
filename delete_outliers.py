import pandas as pd

# Define the input and output file paths
input_file = r"C:\Users\cyril\PycharmProjects\Masterarbeit\subsets_by_date\2024-04-02\2024-04-02_savitzky_gaussian_planar_dist_time_heading_yawRate_noNA.csv"
output_file = r"C:\Users\cyril\PycharmProjects\Masterarbeit\subsets_by_date\2024-04-02\2024-04-02_good.csv"

# Read the CSV file into a DataFrame
df = pd.read_csv(input_file)

# Filter the DataFrame to keep values in the 'yaw_rate_deg_s' column between -3 and 3
filtered_df = df[(df['yaw_rate_deg_s'] >= -3) & (df['yaw_rate_deg_s'] <= 3)]

# Save the filtered DataFrame to a new CSV file
filtered_df.to_csv(output_file, index=False)

print(f"Filtered data saved to {output_file}")
