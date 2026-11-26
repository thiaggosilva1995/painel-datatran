"""Execute: ./venv/bin/python eda_teste.py"""
from dashboard.dados import carregar_dados, evolucao_mensal, mascara_evento, resumo_eventos


def main():
    df = carregar_dados()
    print('COLUNAS REAIS:', df.attrs['colunas_originais'])
    print('\nDIMENSÕES (linhas, colunas tratadas):', df.shape)
    print('\nTIPOS:\n', df.dtypes.to_string())
    print('\nNULOS ANTES DO TRATAMENTO:\n', df.attrs['nulos_originais'])
    print('\nNULOS APÓS TRATAMENTO:\n', df.isna().sum().to_string())
    print('\n5 PRIMEIRAS LINHAS:\n', df.head().to_string(index=False))
    resumo = resumo_eventos(df)
    print('\nTOTAL POR EVENTO (decrescente):\n', resumo[['evento', 'quantidade']].to_string(index=False))
    print('\nTOP 3:\n', resumo[['evento', 'quantidade']].head(3).to_string(index=False))
    selecionados = df.loc[mascara_evento(df.evento, 'cvli') | mascara_evento(df.evento, 'transito') | mascara_evento(df.evento, 'mandados')].copy()
    for categoria, rotulo in [('cvli', 'CVLI'), ('transito', 'Trânsito'), ('mandados', 'Mandados de Prisão Cumpridos')]:
        selecionados.loc[mascara_evento(selecionados.evento, categoria), 'evento'] = rotulo
    print('\nEVOLUÇÃO MENSAL — CVLI, TRÂNSITO E MANDADOS:\n', evolucao_mensal(selecionados).to_string())
    denominador = (resumo.feminino + resumo.masculino).replace(0, float('nan'))
    resumo['feminino_pct'] = (100 * resumo.feminino / denominador).fillna(0).round(2)
    resumo['masculino_pct'] = (100 * resumo.masculino / denominador).fillna(0).round(2)
    print('\nFEMININO X MASCULINO POR EVENTO:\n', resumo[['evento', 'feminino', 'masculino', 'feminino_pct', 'masculino_pct']].to_string(index=False))
    print('\nPercentuais calculados sobre feminino + masculino; não informado fica fora do denominador.')
    print('Quantidade: total, quando preenchido; caso contrário, total_vitima. Total geral mistura unidades e não representa vítimas únicas.')


if __name__ == '__main__':
    main()
