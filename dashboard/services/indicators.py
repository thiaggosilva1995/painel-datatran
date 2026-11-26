import pandas as pd


def number(value, digits=0):
    if pd.isna(value):
        return 'Não informado'
    return f'{value:,.{digits}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def indicators(df):
    n = df.id.nunique()
    sums = {c:df[c].sum(min_count=1) for c in ['mortos','feridos','feridos_graves','feridos_leves','veiculos','pessoas']}
    fatal = int((df.mortos>0).sum())
    items = [('Sinistros registrados',n), ('Óbitos',sums['mortos']), ('Feridos',sums['feridos']), ('Feridos graves',sums['feridos_graves']), ('Feridos leves',sums['feridos_leves']), ('Veículos envolvidos',sums['veiculos']), ('Sinistros fatais (%)',100*fatal/n if n else None), ('Óbitos / 100 sinistros',100*sums['mortos']/n if n else None), ('Pessoas envolvidas',sums['pessoas']), ('Sinistros com óbitos',fatal)]
    out = [{'label':k,'value':number(v,1 if '%' in k else 0)} for k,v in items]
    out.append({'label':'UF com mais sinistros','value':str(df.uf.value_counts().index[0]) if n and df.uf.notna().any() else 'Sem dados'})
    return out

