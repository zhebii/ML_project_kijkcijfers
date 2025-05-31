from datetime import datetime, timedelta, date
import requests
import pandas as pd
import pickle
import numpy as np
import holidays
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

csv_te_voorspellen = './data csv/Input_voor_examen (1).csv'

def ophalenKijkcijferData(startDate, endDate):
  print(f"Ophalen kijkcijfer-data van {startDate.year}-{startDate.month}-{startDate.day} tot {endDate.year}-{endDate.month}-{endDate.day}")
  kijkcijfersData = []
  #elke dag ophalen (startDate is huidige dag)
  while startDate <= endDate:
    datum = f"{startDate.year}-{startDate.month}-{startDate.day}"
    url = f"https://api.cim.be/api/cim_tv_public_results_daily_views?dateDiff={datum}&reportType=north"

    try:
      response = requests.get(url)
      if response.status_code == 200:
        data = response.json()
        programmaLijst = data.get('hydra:member', [])
                        
        for programma in programmaLijst:
          try:
            kijkcijfersData.append({
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
      print(f"error: {e}")
    
    startDate += timedelta(days=1)

  print("KijkcijferData opgehaald")
  df = pd.DataFrame(kijkcijfersData)

  return df

def ophalenWeerData(startDate, endDate):
    latitude = 51.05
    longitude = 3.7167
    today = datetime.today().date()

    hourly_vars = [
        "temperature_2m", "apparent_temperature", "weather_code", "precipitation",
        "rain", "snowfall", "cloud_cover", "windspeed_10m", "sunshine_duration"
    ]
    
    common_params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": hourly_vars,
        "timezone": "Europe/Brussels",
        "temperature_unit": "celsius",
        "precipitation_unit": "mm",
        "windspeed_unit": "kmh"
    }

    def fetch_weather_data(api_url, start, end):
        params = common_params.copy()
        params.update({
            "start_date": start.strftime('%Y-%m-%d'),
            "end_date": end.strftime('%Y-%m-%d')
        })
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json().get("hourly", {})
            df = pd.DataFrame({var: data.get(var, []) for var in hourly_vars})
            df["timestamp"] = pd.to_datetime(data.get("time", []))
            if not df.empty:
                df["hour"] = df["timestamp"].dt.hour
                df["day_of_week"] = df["timestamp"].dt.dayofweek
                df["month"] = df["timestamp"].dt.month
                df["year"] = df["timestamp"].dt.year
            return df
        else:
            print(f"Fout bij ophalen data: {response.status_code}")
            print(response.text)
            return pd.DataFrame()

    dataframes = []

    # Historische data
    if startDate.date() < today:
        print("Ophalen historische data")
        hist_end = min(endDate.date(), today - timedelta(days=1))
        dataframes.append(fetch_weather_data(
            "https://archive-api.open-meteo.com/v1/archive",
            startDate, datetime.combine(hist_end, datetime.min.time())
        ))

    # Forecast data
    if endDate.date() >= today:
        print("Ophalen forecast data")
        forecast_start = max(endDate, datetime.combine(today, datetime.min.time()))
        print(forecast_start)
        dataframes.append(fetch_weather_data(
            "https://api.open-meteo.com/v1/forecast",
            forecast_start, endDate
        ))

    if dataframes:
        print("Weerdata opgehaald")
        return pd.concat(dataframes).sort_values("timestamp").reset_index(drop=True)
    else:
        return pd.DataFrame()

def testCSV(csv):
    df = pd.read_csv(csv, delimiter=';')
    # Kolommen hernoemen
    df = df.rename(columns={
        'Programma': 'description',
        'Zender': 'channel',
        'Datum': 'dateDiff',
        'Start': 'startTime',
        'Duur': 'rLength'
    })
    # Datum en tijd samenvoegen tot datetime
    df['dateDiff'] = pd.to_datetime(df['dateDiff'], dayfirst=True)
    # Starttijd naar HH:MM:SS
    df['startTime'] = df['startTime'].str[:8]
    # Duur naar HH:MM:SS
    df['rLength'] = df['rLength'].apply(lambda x: str(pd.to_timedelta(x)))
    # Voeg dummy kolommen toe als nodig
    df['ranking'] = 0
    df['live'] = 0
    df['Kijkers'] = None

    return df[['dateDiff', 'ranking', 'description', 'channel', 'startTime', 'rLength', 'live']]

teVoorspellen = testCSV(csv_te_voorspellen)

teVoorspellen['dateDiff'] = pd.to_datetime(teVoorspellen['dateDiff'])

end_date = teVoorspellen['dateDiff'].max()
start_date = end_date - timedelta(weeks=3)
histKijkcijfers = ophalenKijkcijferData(start_date, end_date - timedelta(days=1))
histWeerdata = ophalenWeerData(start_date, end_date)

def cleanKijkcijferData(df):

    # Zet 'Kijkers' kolom, als 'rateInK' bestaat
    if 'rateInK' in df.columns:
        df['Kijkers'] = (
            df['rateInK']
            .dropna()
            .astype(str)
            .str.replace('.', '', regex=False)
            .astype(int)
        )
    else:
        df['Kijkers'] = None

    # rLength aanpassen
    df['rLength'] = df['rLength'].astype(str).apply(
    lambda x: x[-8:] if 'days' in x else x.zfill(8)
    )

    # Tijd aanpassen
    tijd_regex = r'^\d{2}:\d{2}:\d{2}$'
    # Omzetten naar datetime
    df['date'] = pd.to_datetime(df['dateDiff']).dt.date
    # Filter rijen met formaat
    df = df[df['startTime'].str.match(tijd_regex, na=False) & df['rLength'].str.match(tijd_regex, na=False)].copy()
    
    # Afleveringlengte naar seconden omzetten 
    df['Lengte_sec'] = pd.to_timedelta(df['rLength']).dt.total_seconds().astype(int)

    # Uren met 24+
    def time_cor(rij):
        tijdArr = rij['startTime'].split(':')
        if int(tijdArr[0]) >= 24:
            tijdArr[0] = str(int(tijdArr[0]) - 24).zfill(2)
            rij['date'] += timedelta(days=1)
        rij['startTime'] = ':'.join(tijdArr)
        return rij
    
    df = df.apply(time_cor, axis=1)

    # 1 kolom voor beide data
    df['FullDate'] = pd.to_datetime(df['date'].astype(str) 
                                    + " " + df['startTime'].astype(str))
    
    # Hour en minute voor join later on
    df['hour'] = pd.to_datetime(df['startTime'], format='%H:%M:%S').dt.hour
    df['minute'] = 0

    # Kolommen verwijderen die niet nodig meer zijn, als ze bestaan
    columns_to_drop = ['startTime', 'rLength', 'rateInK', 'ranking', 'live']
    df.drop([col for col in columns_to_drop if col in df.columns], axis=1, inplace=True)


    # De nieuwe dataframe
    df = df[['FullDate', 'date', 'hour', 'minute', 'channel', 'description', 'Lengte_sec', 'Kijkers']]

    # Hernoemen kolommen
    df.rename(columns={'description': 'Programma', 'channel': 'Kanaal'}, inplace=True)

    return df


def cleanWeerData(df):
  weerData = df
  weerData['timestamp'] = pd.to_datetime(weerData['timestamp'])
  #naar zelfde formaat als kijkcijfer datum
  weerData['datetime'] = weerData['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

  #hour voor join later on
  weerData['hour'] = pd.to_datetime(weerData['datetime']).dt.hour
  weerData['minute'] = pd.to_datetime(weerData['datetime']).dt.minute
  weerData['date'] = pd.to_datetime(weerData['datetime']).dt.date

  #verwijder kolom
  weerData = weerData.drop(columns=['timestamp'])

  weerData = weerData[['datetime', 'date' ,'hour', 'minute', 'temperature_2m', 'apparent_temperature', 
                            'rain', 'snowfall', 'weather_code', 'cloud_cover', 
                            'windspeed_10m', 'sunshine_duration']]

  #hernoemen kolommen
  weerData.rename(columns={'temperature_2m':'Temperatuur', 'apparent_temperature':'Gevoelstemp', 'windspeed_10m': 'Windsnelheid', 'rain':'Regen', 'snowfall': 'Sneeuw', 'weather_code':'Weercode', 'cloud_cover':'Bewolking', 'sunshine_duration':'Zonnenschijn'}, inplace=True)

  return weerData

histWeerdataClean = cleanWeerData(histWeerdata)
histKijkcijfersClean = cleanKijkcijferData(histKijkcijfers)
teVoorspellenClean = cleanKijkcijferData(teVoorspellen)

def mergen(kijkcijfers, weer):
  kijkcijfersWeer = pd.merge(kijkcijfers, weer, on=['date', 'hour'], how='left')
  kijkcijfersWeer = kijkcijfersWeer[['FullDate', 'date', 'hour', 'Kanaal', 'Programma', 'Lengte_sec', 'Kijkers', 'Temperatuur', 'Gevoelstemp', 'Regen', 'Sneeuw', 'Weercode', 'Bewolking', 'Windsnelheid', 'Zonnenschijn']]
  kijkcijfersWeer.dropna(inplace=True)
  return kijkcijfersWeer

histKijkcijfersWeer = mergen(histKijkcijfersClean, histWeerdataClean)

teVoorspellenData = pd.merge(teVoorspellenClean, histWeerdataClean, on=['date', 'hour', 'minute'], how='left')
teVoorspellenData = teVoorspellenData.drop(columns=['datetime', 'minute'])

def tijdFeatures(df):
    df['date'] = pd.to_datetime(df['date'])
    #feestdagen
    feestdagen = holidays.BE()
    df['isFeestdag'] = df['date'].apply(lambda x: 1 if x in feestdagen else 0)
    #dag van de week
    df['Weekdag'] = df['date'].dt.weekday
    #weekend
    df['isWeekend'] = df['Weekdag'].apply(lambda x: 1 if x >= 5 else 0)
    #seizoenen
    df['Seizoen'] = df['date'].apply(seizoenFinder)

    return df

#seizoen
def seizoenFinder(datum):
    inputDatum = datum.date()
    Y = inputDatum.year
    seizoenen = {
        'lente': (date(Y, 3, 20), date(Y, 6, 20)),
        'zomer': (date(Y, 6, 21), date(Y, 9, 22)),
        'herfst':   (date(Y, 9, 23), date(Y, 12, 20)),
        'winter': (date(Y, 12, 21), date(Y + 1, 3, 19)),
    }

    for seizoen, (start, end) in seizoenen.items():
        if start <= inputDatum <= end:
            return seizoen
    return 'winter'

teVoorspellenData = tijdFeatures(teVoorspellenData)
histKijkcijfersWeer = tijdFeatures(histKijkcijfersWeer)
histWeerdataClean = tijdFeatures(histWeerdataClean)
histWeerdataClean.drop(columns=['minute'], inplace=True)

def lagFeatures(df, hist):
  df['Kijkers'] = None
  df['teVoorspellen'] = True
  hist['teVoorspellen'] = False
  df = pd.concat([hist, df], ignore_index=True)
  # Sorteer op tijd binnen elke groep
  df = df.sort_values(['Programma', 'FullDate'])

  df = df.sort_values(['Programma', 'FullDate'])

  # Bereken lag features per programma
  for i in range(1, 4):
      df[f'Kijkers_lag_{i}'] = df.groupby('Programma')['Kijkers'].shift(i)
      df[f'Kijkers_lag_{i}'] = df[f'Kijkers_lag_{i}'].fillna(df.groupby('Programma')['Kijkers'].transform('mean'))

  return df

pred_hist_df = lagFeatures(teVoorspellenData, histKijkcijfersWeer)
print("lagfeatures toevoegen...")
# display(pred_hist_df.dtypes)
pred_hist_df = pred_hist_df[pred_hist_df['teVoorspellen']]
pred_hist_df.drop(columns=['teVoorspellen'], inplace=True)

def oneHot(df):
  with open('./models/oneHotEncoder.pkl', 'rb') as oneHotFile:
    oneHotEnc = pickle.load(oneHotFile)

  lageKard = df[[ 'hour','Kanaal', 'isFeestdag', 'Weekdag', 'Seizoen']]
  dfOneHot = oneHotEnc.transform(lageKard)

  oneHotOutp = pd.DataFrame(dfOneHot.toarray(), 
                            columns=oneHotEnc.get_feature_names_out(), 
                            index=lageKard.index)

  df = df.drop(columns=['hour', 'Kanaal', 'isFeestdag', 'Weekdag', 'Seizoen'])
  df = pd.concat([df, oneHotOutp], axis = 1)
  return df

def target(df):
  #target encoding voor medium kardinaliteiten
  with open('./models/oneHotTarget.pkl', 'rb') as f:
    targetEnc = pickle.load(f)
  medKardinaliteit = df[['date', 'Programma', 'Lengte_sec', 'Temperatuur', 'Gevoelstemp', 'Regen', 'Bewolking', 'Windsnelheid', 'Zonnenschijn']]
  #verdere feature engineering op vorig model
  target = targetEnc.transform(medKardinaliteit)
  df = df.drop(columns=['date', 'Programma', 'Lengte_sec', 'Temperatuur', 'Gevoelstemp', 'Regen', 'Bewolking', 'Windsnelheid', 'Zonnenschijn'])
  f = pd.concat([df, target], axis=1)

  return f

teVoorspellenData = oneHot(pred_hist_df)
print("onehotencoding...")
# Target encoding
targetOneHotEnc = target(teVoorspellenData)
print("targetencoding...")

teVoorspellenProgramma = teVoorspellenData['Programma']
teVoorspellenData = targetOneHotEnc.select_dtypes(include=[np.number])

try:
    with open('./models/optunaBestModel.pkl', 'rb') as file:
        lgbm = pickle.load(file)
except Exception as e:
    print("Kon model niet laden:", e)
    exit(1)

predictions = lgbm.predict(teVoorspellenData)
predictions = np.round(predictions).astype(int)
resultaten = pd.DataFrame({
    'Predicted': predictions,
    'Programma': teVoorspellenProgramma,
})
print(resultaten)