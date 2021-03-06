# from autoviz.AutoViz_Class import AutoViz_Class
# AV = AutoViz_Class()

import numpy as np
from easydict import EasyDict as ed
from tqdm import tqdm
import pandas as pd
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from easydict import EasyDict as ed
from warnings import warn

pd.options.display.max_columns = 100

targhe = [
"FY293YC", "FY295YC", "FY298YC", "FY294YC", "FY296YC", "FV903SK", "FV904SK", "FV906SK", "FV907SK", "FV908SK", "FZ330SC", "FV913SK", "FV914SK", "FY402YC", "FY403YC", "ZB477AN", "ZB473AN", "ZB474AN", "ZB476AN", "ZB475AN", "ZB478AN", "ZB137AR", "ZB139AR", "ZB150AR", "ZB127AR", "ZB132AR", "ZB128AR", "ZB131AR", "ZB130AR", "FY400YC", "ZB135AR", "ZB136AR", "ZB134AR", "ZB373AN", "FY401YC", "CW363HC", "CW367HC", "FP698BP", "FP699BP", "CW365HC", "CW368HC", "CN433CA", "FV989FV", "FV990FV", "FV991FV", "FV995FV", "FV996FV", "FV997FV", "FV992FV", "FV985FV", "FV987FV", "FV988FV", "FV993FV", "FV994FV", "EG181YE", "FV986FV", "EN971TN", "FY299YC", 
]

timestamp_names = ["date", "transaction_date", "Data", "creationDate", "position_timestamp", "snapshot_date_time", "PositionDateTime", "StartDate", "dateDay", "datestamp", "timestampCall", "DataTransazione", "start_timestamp"]
plate_names = ["license_plate", "LicensePlate", "vehiclePlate", "TruckPlate", "Targa", "registration_number"]

veicoli = pd.read_excel("excels/SEA_Flotta_Elenco_Veicoli.xlsx", skiprows=lambda x: x > 341) # il file contiene altre cose dopo
veicoli = veicoli.drop(veicoli.columns[-5:-2], axis=1)[veicoli.TARGA.isin(targhe)]\
          .reset_index(drop=True).rename(columns=lambda x: x.strip().replace("\n", " ").title())
veicoli["plate"] = veicoli.Targa

veicoli["Sistema Gps Tracking"] = veicoli["Sistema Gps Tracking"].str.replace(' ', '').str.split('+')#.unique()
veicoli = veicoli.explode("Sistema Gps Tracking")#.groupby(['Targa', 'Sistema Gps Tracking']).first()

fatture = pd.read_excel("excels/eventi_manutenzioni_esterne (da fatture).xlsx")
fatture.Apertura_commessa = pd.to_datetime(fatture.Apertura_commessa)

VIN_toplate = veicoli[["Targa", "Telaio"]].drop_duplicates().rename({"Targa": "plate", "Telaio": "VIN"}, axis=1).set_index("VIN")

sns.set_style("whitegrid")

def get_args():
    parser = argparse.ArgumentParser(description='Produce analisi di base su una tabella di dati di un fornitore.')
    parser.add_argument("-d", "--data", type=Path, help="Percorso del file (in CSV).", required=True)
    parser.add_argument("--timestamp_name", type=str, default=None, help="Nome della variabile di timestamp (optional).")
    parser.add_argument("--plate_name", type=str, default=None, help="Nome della variabile Targa (optional).")
    parser.add_argument("--cut_date", nargs='?', default=False, const=True, help="Elimina tutti i dati precedenti a maggio 2021.")

    
    return parser.parse_args()

def read_data(path, cut_range=True, drop_duplicates=False, clear_useless=True, verbose=False, **kwargs):
    df = pd.read_csv(path, **kwargs)
    
    if not "plate" in df.columns:
        for p in plate_names:
            if p in df.columns: df["plate"] = df[p]
    if not "plate" in df.columns and "VIN" in df.columns:
        df = df.join(VIN_toplate, on="VIN")
    
    if "plate" in df.columns: df = df[df.plate.isin(targhe)]
    if len(df) == 0: return None
        
    for t in timestamp_names:
        if t in df.columns: df["timestamp"] = df[t]
    
    if "timestamp" in df.columns:
        df.timestamp = pd.to_datetime(df.timestamp, utc=True).dt.tz_localize(None) #.floor('D')
        df["date"] = pd.to_datetime(df.timestamp.dt.date)
        
    if drop_duplicates:
        if "filename" in df.columns:
            df = df.drop("filename", axis=1)
        df = df.drop_duplicates()
        
    if cut_range:
        anomalies = df[df.timestamp < pd.to_datetime("2021-01-01")]
        if verbose:
            print(f"Eliminati {len(anomalies)} record anomali antecedenti al 2021 (in date {' '.join(anomalies.timestamp.dt.strftime('%d/%m/%Y').unique())})")
        df = df.drop(anomalies.index)
    
    if clear_useless == True:
        useless_cols = [c for c in df.columns if len(df[c].unique()) <= 1]
        if verbose:
            print("Misurazioni con valore singolo:")
            print(df[useless_cols].iloc[0,:])
            print("--> Colonne eliminate")
            
        uc = df[useless_cols].iloc[0,:]
        df = df.drop(useless_cols, axis=1)
#         return df.reset_index(drop=True), uc

    return df.reset_index(drop=True)
    
    
def overview(df, timestamp="timestamp", plate="plate", fatture=fatture, clear=True, print_ov=True):
    """
    Restituisce un rassunto del range di date considerato, dei veicoli monitorati e della media delle misurazioni.
    Con clear=True, restituisce il dataframe escluso dalle colonne con valore singolo e un dizionario con il valore fisso acquisito per ognuna di esse.
    """
    date_range = (df[timestamp].max() - df[df[timestamp].dt.year==2021][timestamp].min()).days
    targhe_all = len(df[plate].unique())
    fatture_all = len(fatture[fatture.Targa.isin(df[plate].unique())])
    
    df = df[df[plate].isin(targhe)]
    targhe_cons = len(df[plate].unique())

    daterange = f"    Dati raccolti tra {df[df[timestamp].dt.year==2021][timestamp].min().strftime('%m/%Y')} e {df[timestamp].max().strftime('%m/%Y')}"
    if (df[timestamp].dt.year!=2021).any(): 
        daterange += " (con alcune eccezioni)\n"
    
    distinct_s = (df.drop('filename', axis=1) if 'filename' in df.columns else df).drop_duplicates().shape[0]
    ov = ed({
        "date": daterange,
        "features": df.shape[1],
        "samples": df.shape[0],
        "distinct_samples": distinct_s,
        "targhe": targhe_cons,
        "samples/truck": distinct_s/targhe_cons,
        "samples/day/truck": distinct_s/targhe_cons/date_range,
        "fatture": len(fatture[fatture.Targa.isin(df[plate].unique())]),
    })
    
    
    if print_ov:
        print(f"{ov.date}\n\
        {ov.features} parametri totali monitorati\n\
        {ov.samples} record nel datalake\n\
        {ov.distinct_samples} record non ripetuti\n\
        {ov.targhe} truck di interesse monitorati\n\
        In media {ov['samples/truck']} misurazioni per ogni mezzo su 5 mesi\n\
        In media {ov['samples/day/truck']} misurazioni/giorno/mezzo (dettaglio successivamente)\n\
        {ov.fatture} fatture associate.\n")
    
    
    return ov

    
def plot_date_relplot(df, timestamp="timestamp", plate="plate"):
    warn("'plot_date_relplot' is deprecated, use 'draw_date_relplot' instead", DeprecationWarning, stacklevel=2)
    return draw_date_relplot(df, timestamp="timestamp", plate="plate")
    
    
def draw_date_relplot(df, timestamp="timestamp", plate="plate", height=8):
    if not "date" in df.columns:
        df["date"] = df[timestamp].dt.date
    key = df.columns[-2]
    df = df.sort_values(by="date").groupby([plate, "date"], as_index=False)[key].count()
    df['c'] = df[key] / df[key].max()
    
    g = sns.relplot(
        data=df,
        x="date", y=plate, hue="c", size="c",
        palette="vlag", hue_norm=(-1, 1), edgecolor=".7",
        height=height, sizes=(3*height, 18*height), size_norm=(-.02*height, .08*height), aspect=1.5
    )

    for t in g._legend.get_texts():
        t.set_text(int(float(t.get_text())*df[key].max()))
    g._legend.set_title("Samples")
    return g


def draw_correlation(df, figsize=(10,8)):
    correlations = df.corr()

    fig, ax = plt.subplots(figsize=figsize)
    mask = np.zeros_like(correlations)
    mask[np.triu_indices_from(mask)] = True
    heatmap = sns.heatmap(correlations.iloc[1:,:-1], annot=True, fmt='.2f', linewidths=0.5,
                mask=mask[1:,:-1], ax=ax, cmap=sns.diverging_palette(10, 150, s=90, n=7),
                robust=True, vmin=-1)#, annot_kws={"size": 10})
    plt.tight_layout()
    return ax
    
    
def draw_report(df, timestamp="timestamp", plate="plate", fatture=fatture, per_day=True, figsize=(22,9)):
    report = df.groupby(plate).agg({
    timestamp: ["min", "max", 
                "count", pd.Series.nunique
               ],
    }).droplevel(0, axis=1)

    report["fatture"] = report.apply(lambda x: fatture[(fatture.Targa==x.name)&(fatture.Apertura_commessa.dt.date>=x['min'].date())&(fatture.Apertura_commessa.dt.date<=x['max'].date())].ID.count(), axis=1)
    report = report.reset_index().sort_values(by=plate)
    df = df.sort_values(by=plate)
    
    m1 = "misure"
    m2 = "misure[distinte]"
    
    if per_day:
        report["misure/giorno"] = report["count"] / (report['max'] - report['min']).dt.days
        report["misure[distinte]/giorno"] = report["nunique"] / (report['max'] - report['min']).dt.days
        m1 += "/giorno"
        m2 += "/giorno"
    else:
        report = report.rename(columns={"count": m1, "nunique": m2})
        
    fig, ax = plt.subplots(1,4, figsize=figsize, sharey=True)
    palette = None
    sns.scatterplot(data=df, x=timestamp, y=plate, palette=palette, ax=ax[0], zorder=3, s=10)
    sns.scatterplot(data=report, x="min", y=plate, palette=palette, ax=ax[0], zorder=4)
    sns.scatterplot(data=report, x="max", y=plate, palette=palette, ax=ax[0], zorder=4)
    ax[0].hlines(data=report, y=plate, xmin="min", xmax="max", linewidth=5, color='lightblue')
    sns.barplot(data=report, x=m1, y=plate, palette=palette, ax=ax[1])
    sns.barplot(data=report, x=m2, y=plate, palette=palette, ax=ax[2])
    sns.barplot(data=report, x="fatture", y=plate, palette=palette, ax=ax[3])

    ax[0].tick_params(axis='x', rotation=90)
    ax[0].set_xlabel("Date range")
    for a in ax:
        a.set_ylabel("")
        a.set_xlabel(a.get_xlabel(), size=17)
        sns.despine(trim=True)
        a.yaxis.grid("both")

    plt.tight_layout()
    plt.close()
    return fig
#     fig.savefig(outdir / "report.png")


if __name__ == '__main__':
    args = get_args()
    outdir = Path(args.data.stem)
    outdir.mkdir(esists_ok=True, parents=True)
    
    fatture = ...
    df = read_data(args.data)
    overview(df)
    
    draw_report(df)
    
    
    
    