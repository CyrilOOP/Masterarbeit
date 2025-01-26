import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the CSV file
file_path = "subsets_by_date/2024-04-02/2024-04-02_dist_planar_time_heading.csv"  # Replace with the path to your CSV file
df = pd.read_csv(file_path)

# Select every 50th point
step = 150
df_subset = df.iloc[::step]

# Plot the data
plt.figure(figsize=(10, 6))

# Plot x, y (position)
plt.plot(df['x'], df['y'], '-', label='Position (x, y)', markersize=2)

# Add quiver plot for theta (heading) for every 50 points
u = np.cos(np.radians(df_subset['heading_deg']))  # X-component of heading
v = np.sin(np.radians(df_subset['heading_deg']))  # Y-component of heading
plt.quiver(df_subset['x'], df_subset['y'], u, v, color='r', scale=10, label='Heading in degrees)')

# Plot settings
plt.title('Position and Heading (Sampled Every 50 Points)', fontsize=16)
plt.xlabel('x (Position)', fontsize=14)
plt.ylabel('y (Position)', fontsize=14)
plt.grid(True)
plt.legend(fontsize=12)
plt.axis('equal')

# Show plot
plt.show()
