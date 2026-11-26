import io
from functools import lru_cache
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import pandas as pd
from django.conf import settings
from .data_cleaning import clean

MAX_SIZE = 30 * 1024 * 1024


def read_file(source, name):
    suffix = Path(name).suffix.lower()
    if suffix == '.zip':
        try:
            with ZipFile(source) as z:
                files = [i for i in z.infolist() if not i.is_dir()]
                if len(files) != 1 or not files[0].filename.lower().endswith('.csv'):
                    raise ValueError('O ZIP deve conter exatamente um CSV e nenhum outro arquivo.')
                if files[0].file_size > MAX_SIZE:
                    raise ValueError('CSV descompactado excede 30 MB.')
                content = z.read(files[0])
            return read_file(io.BytesIO(content), 'base.csv')
        except BadZipFile as exc:
            raise ValueError('Arquivo ZIP inválido.') from exc
    if suffix == '.xlsx':
        # XLSX também é ZIP: limita expansão antes de abrir o workbook.
        with ZipFile(source) as z:
            if sum(i.file_size for i in z.infolist()) > 100 * 1024 * 1024:
                raise ValueError('Planilha descompactada excede 100 MB.')
        source.seek(0)
        return pd.read_excel(source, engine='openpyxl')
    if suffix != '.csv':
        raise ValueError('Use CSV, XLSX ou ZIP contendo um CSV.')
    content = source.read()
    try:
        return pd.read_csv(io.BytesIO(content), sep=';', encoding='utf-8-sig')
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(content), sep=';', encoding='latin1')


@lru_cache(maxsize=2)
def _load(path, stamp):
    with open(path, 'rb') as source:
        return clean(read_file(source, path))


def load():
    active = settings.BASE_DIR / 'data/processed/active.csv'
    path = active if active.exists() else settings.BASE_DIR / 'data/datatran2026.csv'
    df, report = _load(str(path), path.stat().st_mtime_ns)
    return df.copy(), report.copy()
