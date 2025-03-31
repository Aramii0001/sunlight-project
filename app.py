import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from astral import LocationInfo
from astral.sun import sun
from astral.location import Location
import datetime
import pytz

# --- Config ---
st.set_page_config(page_title="Sunlight Reflection Simulator", layout="wide")

# --- Title ---
st.title("🪞 Sunlight Reflection Visualizer")
st.write("Enter location and direction to simulate mirror practicality at different times of day.")

# --- Sidebar Inputs ---
st.sidebar.header("🔧 Input Settings")
city_name = st.sidebar.text_input("City Name", value="New York")
country = st.sidebar.text_input("Country", value="USA")
latitude = st.sidebar.number_input("Latitude", value=40.7128)
longitude = st.sidebar.number_input("Longitude", value=-74.0060)
timezone = st.sidebar.text_input("Time Zone", value="America/New_York")
street_dir = st.sidebar.selectbox("Street Orientation", ["North-South", "East-West"])
building_face = st.sidebar.selectbox("Building Facing", ["East", "West", "North", "South"])
date = st.sidebar.date_input("Date", value=datetime.date(2025, 3, 27))

# --- Determine sunrise/sunset ---
loc = LocationInfo(city_name, country, timezone, latitude, longitude)
location = Location(loc)
s = sun(location.observer, date=date, tzinfo=pytz.timezone(timezone))
sunrise = s['sunrise']
sunset = s['sunset']
total_hours = int((sunset - sunrise).seconds / 3600) + 1

# --- Time Slider ---
hour_index = st.slider("Select Time of Day (Hour from Sunrise)", 0, total_hours - 1)
dt = sunrise + datetime.timedelta(hours=hour_index)

# --- Compute Sun Position ---
azimuth = location.solar_azimuth(dt)
elevation = location.solar_elevation(dt)

st.subheader(f"☀️ Sun Position at {dt.strftime('%H:%M')}")
st.write(f"Azimuth: {azimuth:.2f}°, Elevation: {elevation:.2f}°")

# --- Mirror Simulation (Grid) ---
rows, cols = 10, 5
dy, dz = 1.5, 1.5
mirror_max_phi = 50
mirror_max_theta = 50

# Direction config
facing_config = {
    "east":  {"azimuth_range": [(45, 135)], "wall_axis": "x", "target_offset": [10, 0]},
    "south": {"azimuth_range": [(135, 225)], "wall_axis": "y", "target_offset": [0, 10]},
    "west":  {"azimuth_range": [(225, 315)], "wall_axis": "x", "target_offset": [-10, 0]},
    "north": {"azimuth_range": [(315, 360), (0, 45)], "wall_axis": "y", "target_offset": [0, -10]},
}

# Parse facing direction
facing = building_face.lower()
cfg = facing_config[facing]
wall_axis = cfg["wall_axis"]
target_offset = cfg["target_offset"]

# Skip if sun is behind the building or too low
visible = elevation > 0 and any(
    (start <= azimuth <= end) if start < end else (azimuth >= start or azimuth <= end)
    for start, end in cfg["azimuth_range"]
)

if not visible:
    st.warning("☁️ The sun is not in front of this building face at this time.")
else:
    theta_sun = np.radians(elevation)
    phi_sun = np.radians(azimuth)
    sun_vector = np.array([
        np.cos(theta_sun) * np.cos(phi_sun),
        np.cos(theta_sun) * np.sin(phi_sun),
        np.sin(theta_sun)
    ])
    sun_vector = sun_vector / np.linalg.norm(sun_vector)

    effort_grid = np.zeros((rows, cols))
    for i in range(rows):
        for j in range(cols):
            if wall_axis == "x":
                y = j * dy - (cols - 1) * dy / 2
                z = i * dz + 2.0
                window_pos = np.array([0.0, y, z])
                target_pos = np.array([target_offset[0], y + target_offset[1], 0.0])
            else:
                x = j * dy - (cols - 1) * dy / 2
                z = i * dz + 2.0
                window_pos = np.array([x, 0.0, z])
                target_pos = np.array([x + target_offset[0], target_offset[1], 0.0])

            incident = -sun_vector
            outgoing = target_pos - window_pos
            outgoing = outgoing / np.linalg.norm(outgoing)
            normal = incident + outgoing
            normal = normal / np.linalg.norm(normal)

            theta = np.degrees(np.arccos(normal[2]))
            phi = np.degrees(np.arctan2(normal[1], normal[0]))
            
            # Effort = 0 if aligned, 1 if at limit
            theta_effort = abs(theta - 90) / mirror_max_theta
            phi_effort = abs(phi) / mirror_max_phi
            effort_score = min(1.0, (theta_effort + phi_effort) / 2)
            
            if abs(phi) > mirror_max_phi or abs(theta - 90) > mirror_max_theta:
                effort_score = 1.0  # Red = not feasible

            effort_grid[i, j] = effort_score

    # Plot heatmap
    fig, ax = plt.subplots(figsize=(6, 5))
    cmap = plt.get_cmap("plasma")
    cax = ax.imshow(effort_grid, cmap=cmap, origin="lower", vmin=0, vmax=1)
    ax.set_title("Mirror Effort Grid (0 = easy, 1 = impossible)")
    ax.set_xlabel("Window Column")
    ax.set_ylabel("Window Row")
    fig.colorbar(cax, label="Effort Score")
    st.pyplot(fig)

    percent_working = 100 * np.sum(effort_grid < 1.0) / (rows * cols)
    st.success(f"✅ {percent_working:.1f}% of mirrors can reflect light at this time.")
