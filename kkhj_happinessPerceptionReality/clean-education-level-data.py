import pandas as pd
import pycountry as pyc

def get_means():
    df = pd.read_csv("data/educationLevel.csv")
    df.rename(columns={'TIME': 'Year'}, inplace=True)
    mask = (df['Year'] >= 2012) & (df['Year'] <= 2021)
    df = df[mask]
    df = (df.groupby(['LOCATION', 'Year'], as_index=False))["Value"].mean()
    df['LOCATION'] = df['LOCATION'].apply(lambda x: pyc.countries.get(alpha_3=x).name if pyc.countries.get(alpha_3=x) != None else None)
    df.rename(columns={'LOCATION': 'Country'}, inplace=True)
    return df

if __name__ == "__main__":
    get_means()