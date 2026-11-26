import json


def map_data(df):
    valid=df.loc[df.geo_valida]
    # Amostra determinística explicitamente identificada; limites só afetam o mapa.
    sample=valid.sample(n=min(4000,len(valid)),random_state=26)
    return {'total':len(valid),'shown':len(sample),'points':json.loads(sample[['latitude','longitude','municipio','uf','mortos','br']].to_json(orient='records'))}
