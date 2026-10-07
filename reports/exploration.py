
import pandas as pd
import numpy as np
import requests
import json
import os

url_api_dpe_existants = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines"
url_api_dpe_neufs = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe02neuf/lines"




def set_params(page:int=None,size=10000,select:str=None,q:str=None,q_field:str=None,qs:str=None,params:dict=None)-> dict:
    """ function set params for the api request
    @param page: int, page number to request
    @param select: str, fields to select
    @param q: str, query string
    @param q_field: str, field to query
    @param qs: str, query string
    @param params: dict, additional parameters
    @return: dict, parameters for the api request
    """
    if params is None:
        params={
            "page": page if page is not None else None,
            "size": size if size is not None else None,
            "select": select if select is not None else None,
            "q": q if q is not None else None,
        "q_fields": q_field if q_field is not None else None,
        "qs": qs if qs is not None else None
    }
    return params

def req_api(url:str,size=10000,page:int=None,select:str=None,q:str=None,q_field:str=None,qs:str=None,params:dict=None)-> pd.DataFrame:
    """ function req api and return a dataframe with the data
    @param url: str, url of the api
    @param page: int, page number to request
    @param select: str, fields to select
    @param q: str, query string
    @param q_field: str, field to query
    @param qs: str, query string
    @param params: dict, additional parameters
    @return: pd.DataFrame, dataframe with the data
    """
    params = set_params(page=page,select=select,q=q,q_field=q_field,qs=qs,params=params)
        
    rep = requests.get(url, params=params)
    try:
        rep.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Erreur lors de la requête : {rep.status_code} - {e}")
        return pd.DataFrame()
    if rep.status_code == 200:
        content = rep.json()
        df = pd.DataFrame(content['results'])
        print(f"nb line : {content['total']}")
        print(f"size data collected : {len(df)}, {len(df.columns) if not df.empty else 0}")
        return df

def get_nb_lines(url:str,page:int=None,size=10000,select:str=None,q:str=None,q_field:str=None,qs:str=None,params:dict=None)-> int:
    params = set_params(page=page,select=select,q=q,q_field=q_field,qs=qs,params=params)
    rep = requests.get(url, params=params)
    try:
        rep.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Erreur lors de la requête : {rep.status_code} - {e}")
        return 0
    if rep.status_code == 200:
        content = rep.json()
        return content['total']


data_raw = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
df_departements = pd.read_csv(os.path.join(data_raw, "codes_departements.csv"),dtype="str")

df_departements["nb_lignes"] = np.nan

for index, cp in df_departements["code_departement"].items():
    print(f"<==code departement : {cp}==>")
    nb = get_nb_lines(url_api_dpe_existants,page=1,size=10000, qs=f"code_departement_ban:{cp}")
    print(f"code departement : {cp}, nb lignes : {nb}")
    df_departements.loc[index, "nb_lignes"] = nb

df_departements = df_departements.sort_values(by="nb_lignes",ascending=False)
df_departements.to_csv(os.path.join(data_raw, "codes_departements_nb_lignes.csv"),index=False)