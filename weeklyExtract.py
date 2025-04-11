import csv
from datetime import datetime, timedelta
import os
import requests

# Vandaag en 7 dagen geleden
end_date = datetime.today()
start_date = end_date - timedelta(days=6)

script_dir = os.path.dirname(os.path.abspath(__file__))
output_file = os.path.join(script_dir, "data csv", "kijkcijfersdataraw.csv")
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Lees bestaande data om duplicaten te vermijden
bestaande_data = set()
if os.path.exists(output_file):
    with open(output_file, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['dateDiff'], row['description'], row['startTime'])
            bestaande_data.add(key)

# Open CSV om toe te voegen
with open(output_file, mode='a', newline='', encoding='utf-8-sig') as file:
    fieldnames = [
        'dateDiff', 'ranking', 'description', 'channel',
        'startTime', 'rLength', 'rateInK', 'live'
    ]
    writer = csv.DictWriter(file, fieldnames=fieldnames)

    # Voeg header toe als het bestand nog leeg is
    if os.path.getsize(output_file) == 0:
        writer.writeheader()

    # Loop over elke dag van de afgelopen 7 dagen
    current_date = start_date
    while current_date <= end_date:
        datum = current_date.strftime("%Y-%m-%d")
        url = f"https://api.cim.be/api/cim_tv_public_results_daily_views?dateDiff={datum}&reportType=north"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                programma_lijst = data.get('hydra:member', [])

                for programma in programma_lijst:
                    key = (
                        programma.get('dateDiff'),
                        programma.get('description'),
                        programma.get('startTime')
                    )
                    if key not in bestaande_data:
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
                            bestaande_data.add(key)
                        except Exception as e:
                            print(f"❌ Fout bij schrijven van programma op {datum}: {e}")
            else:
                print(f"⚠️ Geen data voor {datum} (status {response.status_code})")

        except Exception as e:
            print(f"❌ Fout bij ophalen data voor {datum}: {e}")

        current_date += timedelta(days=1)

print("✅ Data opgehaald en toegevoegd aan CSV.")
