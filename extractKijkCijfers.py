import csv
from datetime import datetime, timedelta
import pandas as pd
import os
import requests

start_date = datetime(2016, 10, 1)
end_date = datetime.today()

script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, "./data csv/kijkcijfersdataraw.csv")

os.makedirs(os.path.dirname(output_file), exist_ok=True)


with open(output_file, mode='w', newline='', encoding='utf-8-sig') as file:
    fieldnames = [
    'dateDiff', 'ranking', 'description', 'channel', 
    'startTime', 'rLength', 'rateInK', 'live'
    ]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    # Loop door elke dag
    current_date = start_date
    while current_date <= end_date:
        datum = f"{current_date.year}-{current_date.month}-{current_date.day}"
        url = f"https://api.cim.be/api/cim_tv_public_results_daily_views?dateDiff={datum}&reportType=north"
            
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                programma_lijst = data.get('hydra:member', [])
                        
                for programma in programma_lijst:
                    try:
                        writer.writerow({
                        'dateDiff': programma.get('dateDiff'),
                        'ranking': programma.get('ranking'),
                        'description': programma.get('description'),
                        'channel': programma.get('channel'),
                        'startTime': programma.get('startTime'),
                        'rLength': programma.get('rLength'),
                        'rateInK': programma.get('rateInK'),
                        'live': programma.get('live')
                        })
                                    
                    except Exception as e:
                        print(f"error {datum}: {e}")         
            else:
                print(f"no data {datum}")
                        
        except Exception as e:
            print(f"error {datum}: {e}")
            
        current_date += timedelta(days=1)
print("data opgehaald")