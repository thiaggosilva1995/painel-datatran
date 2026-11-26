FIELDS = {'uf':'UF', 'municipio':'Município', 'br':'Rodovia BR', 'mes':'Mês', 'dia_semana':'Dia da semana', 'causa_acidente':'Causa registrada', 'tipo_acidente':'Tipo de sinistro', 'classificacao_acidente':'Classificação', 'fase_dia':'Fase do dia', 'condicao_metereologica':'Meteorologia', 'tipo_pista':'Tipo de pista', 'tracado_via':'Traçado', 'regional':'Regional', 'delegacia':'Delegacia', 'uop':'UOP'}


def apply(df, params, pb=False):
    result = df.loc[df.uf.eq('PB')].copy() if pb else df.copy()
    for c in FIELDS:
        if params.get(c) and not (pb and c == 'uf'):
            if c == 'br':
                result = result.loc[result[c].astype('string').str.replace(r'\.0$', '', regex=True).eq(params[c])]
            else:
                result = result.loc[result[c].eq(params[c])]
    for key, operator in [('inicio', 'ge'), ('fim','le')]:
        if params.get(key):
            import pandas as pd
            date = pd.to_datetime(params[key], errors='coerce')
            result = result.loc[getattr(result.data_inversa, operator)(date)]
    for key, operator in [('hora_inicio','ge'), ('hora_fim','le')]:
        if params.get(key):
            try:
                result = result.loc[getattr(result.hora,operator)(int(params[key]))]
            except ValueError:
                result = result.iloc[0:0]
    if params.get('q'):
        q = params['q'][:100]
        mask = result.municipio.str.contains(q, case=False, regex=False, na=False)
        for c in ['id','br']:
            mask |= result[c].astype('string').str.contains(q, regex=False, na=False)
        result = result.loc[mask]
    return result


def options(df, params, pb=False):
    scoped = df.loc[df.uf.eq('PB')] if pb else df
    if params.get('uf') and not pb:
        scoped = scoped.loc[scoped.uf.eq(params['uf'])]
    out = []
    for key,label in FIELDS.items():
        base = scoped if key in ['municipio','br','delegacia','uop'] else df
        vals = base[key].dropna().unique()
        vals = sorted(str(v).removesuffix('.0') if key == 'br' else str(v) for v in vals)
        out.append({'key':key,'label':label,'values':vals,'selected':'PB' if pb and key=='uf' else params.get(key,'')})
    return out
