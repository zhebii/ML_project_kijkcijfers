import requests
import csv
import os

url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": 51.05,
    "longitude": 3.7167,
    "start_date": "2016-10-01",
    "end_date": "2025-04-10",
    "hourly": "temperature_2m,apparent_temperature,rain,snowfall,weather_code,cloud_cover,wind_speed_10m,sunshine_duration",
    "timezone": "auto"
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    hourly_data = data.get("hourly", {})
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(script_dir, ".", "data csv", "weerdataraw.csv")
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    #open csv
    with open(csv_file_path, mode="w", newline="") as file:
        writer = csv.writer(file)

        #header csv
        header = ["timestamp", "temperature_2m", "apparent_temperature", "rain", "snowfall", "weather_code", "cloud_cover", "wind_speed_10m", "sunshine_duration"]
        writer.writerow(header)

        #naar csv schrijven
        for i in range(len(hourly_data.get("temperature_2m", []))):
            row = [
                hourly_data.get("time", [])[i],
                hourly_data.get("temperature_2m", [])[i],
                hourly_data.get("apparent_temperature", [])[i],
                hourly_data.get("rain", [])[i],
                hourly_data.get("snowfall", [])[i],
                hourly_data.get("weather_code", [])[i],
                hourly_data.get("cloud_cover", [])[i],
                hourly_data.get("wind_speed_10m", [])[i],
                hourly_data.get("sunshine_duration", [])[i]
            ]
            writer.writerow(row)

    print(f"Data weggeschreven: {csv_file_path}")
else:
    print(f"Failed status code: {response.status_code}")