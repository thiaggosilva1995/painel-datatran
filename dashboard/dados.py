"""Leitura compartilhada pela análise exploratória e pelo painel."""
from functools import lru_cache
from pathlib import Path
import re
import unicodedata

import pandas as pd

PLANILHA = Path(__file__).resolve().parent.parent / 'data' / 'BancoVDE 2025.xlsx'
NUMERICAS = ['feminino', 'masculino', 'nao_informado', 'total_vitima', 'total', 'total_peso']


def normalizar_nome(nome):
    texto = unicodedata.normalize('NFKD', str(nome).strip().lower())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '_', texto).strip('_')


@lru_cache(maxsize=1)
def _carregar(caminho, modificacao):
    df = pd.read_excel(caminho, engine='openpyxl')
    originais = df.columns.tolist()
    df.columns = [normalizar_nome(c) for c in df.columns]
    obrigatorias = {'uf', 'municipio', 'evento', 'data_referencia', 'abrangencia', *NUMERICAS[:-1]}
    faltantes = obrigatorias - set(df.columns)
    if faltantes:
        raise ValueError(f'Colunas ausentes na planilha: {sorted(faltantes)}')
    df.attrs['colunas_originais'] = originais
    df.attrs['nulos_originais'] = df.isna().sum().to_dict()
    df['data_referencia'] = pd.to_datetime(df['data_referencia'], dayfirst=True, errors='coerce', format='mixed')
    # Alguns eventos informam vítimas; outros informam ocorrências em total.
    total_original = pd.to_numeric(df['total'], errors='coerce')
    for coluna in NUMERICAS:
        if coluna in df:
            df[coluna] = pd.to_numeric(df[coluna], errors='coerce').fillna(0)
    df['quantidade'] = total_original.fillna(df['total_vitima']).fillna(0)
    for coluna in ['uf', 'municipio', 'evento', 'abrangencia']:
        df[coluna] = df[coluna].astype('string').str.strip().replace('', pd.NA).fillna('Não informado')
    return df


def carregar_dados(caminho=PLANILHA):
    """Retorna dados tratados; não altere o DataFrame compartilhado diretamente.

    O cache é renovado quando o arquivo muda. Para editar, use .copy().
    """
    caminho = Path(caminho)
    return _carregar(str(caminho), caminho.stat().st_mtime_ns)


def resumo_eventos(df):
    return (df.groupby('evento', as_index=False)[['quantidade', 'feminino', 'masculino', 'nao_informado']]
            .sum().sort_values('quantidade', ascending=False))


def evolucao_mensal(df):
    validos = df.loc[df['data_referencia'].notna(), ['data_referencia', 'evento', 'quantidade']].copy()
    validos['mes'] = validos['data_referencia'].dt.to_period('M').dt.to_timestamp()
    return validos.pivot_table(index='mes', columns='evento', values='quantidade', aggfunc='sum', fill_value=0).sort_index()


def mascara_evento(eventos, categoria):
    nomes = eventos.map(normalizar_nome)
    padroes = {
        'cvli': r'cvli|crimes?_violentos?_letais?_intencionais?|^homicidio_doloso$|^lesao_corporal_seguida_de_morte$|^roubo_seguido_de_morte',
        'transito': r'transito',
        'mandados': r'mandad.*pris.*cumpr',
    }
    return nomes.str.contains(padroes[categoria], regex=True, na=False)
