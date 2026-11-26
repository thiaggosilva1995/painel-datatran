"""Validação conservadora: contagens desconhecidas continuam nulas."""
import pandas as pd

COLUMNS = 'id data_inversa dia_semana horario uf br km municipio causa_acidente tipo_acidente classificacao_acidente fase_dia sentido_via condicao_metereologica tipo_pista tracado_via uso_solo pessoas mortos feridos_leves feridos_graves ilesos ignorados feridos veiculos latitude longitude regional delegacia uop'.split()
COUNTS = 'pessoas mortos feridos_leves feridos_graves ilesos ignorados feridos veiculos'.split()


def clean(raw):
    missing = set(COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError('Colunas obrigatórias ausentes: ' + ', '.join(sorted(missing)))
    df = raw[COLUMNS].copy()
    nulls = df.isna().sum().to_dict()
    for c in df.select_dtypes(include=['object', 'string']).columns:
        df[c] = df[c].astype('string').str.strip().replace('', pd.NA)
    df['id'] = pd.to_numeric(df.id, errors='coerce')
    df['id'] = df.id.where((df.id > 0) & (df.id % 1 == 0)).astype('Int64')
    df['data_inversa'] = pd.to_datetime(df.data_inversa, errors='coerce', format='mixed', dayfirst=False)
    times = pd.to_datetime(df.horario, format='%H:%M:%S', errors='coerce')
    df['hora'] = times.dt.hour.astype('Int64')
    for c in ['km', 'latitude', 'longitude', 'br', *COUNTS]:
        df[c] = pd.to_numeric(df[c].astype('string').str.replace(',', '.', regex=False), errors='coerce')
        if c in COUNTS or c in ['km', 'br']:
            df[c] = df[c].where(df[c] >= 0)
        if c in COUNTS:
            df[c] = df[c].where(df[c] % 1 == 0)
    geo = df.latitude.between(-34, 6) & df.longitude.between(-74, -28)
    df['geo_valida'] = geo
    df['uf'] = df.uf.str.upper()
    df['municipio'] = df.municipio.str.upper()
    invalid = df.id.isna() | df.data_inversa.isna()
    duplicates = df.loc[~invalid].duplicated('id', keep='first')
    report = dict(recebidos=len(df), rejeitados=int(invalid.sum()), duplicados=int(duplicates.sum()),
                  coordenadas_invalidas=int((~geo).sum()), horarios_invalidos=int(times.isna().sum()),
                  feridos_inconsistentes=int((df.feridos.notna() & df.feridos_leves.notna() & df.feridos_graves.notna() & (df.feridos != df.feridos_leves + df.feridos_graves)).sum()),
                  nulos_originais={k: int(v) for k,v in nulls.items()},
                  nulos_tratados={k: int(v) for k,v in df.isna().sum().items()})
    df = df.loc[~invalid].drop_duplicates('id', keep='first').copy()
    df['mes'] = df.data_inversa.dt.strftime('%Y-%m')
    df['semana'] = df.data_inversa.dt.dayofweek
    report['aceitos'] = len(df)
    return df, report
