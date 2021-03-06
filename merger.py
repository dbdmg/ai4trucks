from tqdm import tqdm
import pandas as pd
from pathlib import Path
from joblib import Parallel, delayed

"""
Questo script salva i file di ogni fornitore (nel formato 'FORNITORE/SOTTOCARTELLA/file.json') in files
CSV nella cartella 'dataset'.
"""

ignore_list = [#"VISIRUN", "SCANIA", "MOVIMATICA"
               'CGTISAT_INFOold', 'TIMBRATURE_ingestioneventhub', 'IP' # different folder structure
              ]
dataset = Path("dataset2")
DL_path = Path("SEA Data Lake")
# DL_path = Path("SDL_2")

dataset.mkdir(exist_ok=True, parents=True)

def merge_json(path, output, p=None):
    if output.exists(): return
    df = pd.DataFrame([])
    suffix = f"*-{p}.json" if p is not None else "*json"
    for f in tqdm(sorted(path.glob(suffix)),
                        desc=f"{path.parent.stem}/{path.stem}[{suffix}]"
                 ):
        try:
            tmp = pd.read_json(f)
            tmp["filename"] = f.stem.rsplit('-', 1)[0]
            df = df.append(tmp) #TODO: da fare meglio, questo permette di aggregare dati come VISIRUN
        except:
            tmp = pd.read_json(f, typ='series')
            tmp["filename"] = f.stem.rsplit('-', 1)[0]
            df = df.append(tmp, ignore_index=True)
        
    df.to_csv(output, index=False)
    return

for fornitore in DL_path.iterdir():
#     if fornitore.name != "SEA_DL_Visirun": continue
    if fornitore.name in ignore_list: continue

    for tab in fornitore.iterdir():
        if tab.name != "Route": continue
        if "old" in tab.stem.lower(): continue
        if not tab.is_dir(): continue
            
        full_output = dataset / f"{fornitore.stem}_{tab.stem}.csv"
        if full_output.exists(): continue
            
        partitions = set([p.stem.split("-")[-1] for p in tab.iterdir()])
        print(partitions)
        ciao
        if len(partitions) < 2:
            partitions = set(["-".join(p.stem.split("-")[-2:]) for p in tab.iterdir()])
        
        
        Parallel(n_jobs=16)(delayed(merge_json)(tab, 
                                                output=dataset / f"{fornitore.stem}_{tab.stem}_{p}.csv",
                                                p=p
                                               ) for p in partitions)
        
        full_merged = pd.DataFrame()
        
        for df in dataset.glob(f"{fornitore.stem}_{tab.stem}_*"):
            full_merged = full_merged.append(pd.read_csv(df))
            
        full_merged.to_csv(full_output, index=False)

#         merge_json(tab, output, p)
