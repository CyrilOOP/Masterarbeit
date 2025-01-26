import pandas as pd
import matplotlib.pyplot as plt

# File path
file_path = 'subsets_by_date/2024-04-02/2024-04-02_dist_planar_spline_time_spline_time_dist_planar.csv'

# Load the data
df = pd.read_csv(file_path)

# Convert the time column to a datetime object for better visualization
df['DatumZeit'] = pd.to_datetime(df['DatumZeit'], errors='coerce')

# Drop rows with missing data in relevant columns
df = df.dropna(subset=['DatumZeit', 'Gier', 'yaw_rate'])

# Plot Gier and yaw_rate for comparison
plt.figure(figsize=(12, 6))
plt.plot(df['DatumZeit'], df['Gier'], label='Gier', alpha=0.8)
plt.plot(df['DatumZeit'], df['yaw_rate'], label='Yaw Rate', alpha=0.8)
plt.xlabel('Time')
plt.ylabel('Value')
plt.title('Comparison of Gier and Yaw Rate over Time')
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()
