from .indicators import number


def insights(df):
    if df.empty:
        return []
    out = [f'Entre {df.data_inversa.min():%d/%m/%Y} e {df.data_inversa.max():%d/%m/%Y}, o recorte contém {number(df.id.nunique())} sinistros; {number((df.mortos > 0).sum())} tiveram óbitos registrados.']
    for c,label in [('uf','UF'),('causa_acidente','Causa registrada'),('br','Rodovia BR'),('hora','Hora')]:
        counts = df[c].value_counts()
        if len(counts):
            out.append(f'{label}: {counts.index[0]} concentra {number(counts.iloc[0])} sinistros ({number(counts.iloc[0]/len(df)*100,1)}% do recorte).')
    deaths = df.groupby(['uf','municipio']).mortos.sum(min_count=1).dropna().sort_values(ascending=False)
    if len(deaths):
        out.append(f'{deaths.index[0][1]} ({deaths.index[0][0]}) lidera a contagem municipal de óbitos: {number(deaths.iloc[0])}.')
    return out
