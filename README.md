# DATATRAN · Inteligência viária

Dashboard Django local conectado exclusivamente ao CSV DATATRAN. O módulo legado `dashboard/dados.py`, o template antigo e os scripts EDA foram preservados; as novas rotas não dependem da base VDE.

## Executar no Ubuntu/WSL2

```bash
cd painel-datatran
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py processar_datatran
python manage.py runserver
```

Abra http://127.0.0.1:8000. Para verificar:

```bash
python manage.py check
python manage.py test dashboard
```

## Navegação

- `/`: visão geral, 8 gráficos e indicadores calculados.
- `/temporal/`: séries, calendários, heatmaps e distribuição horária.
- `/geographic/`: mapa com clustering e densidade, rankings e dispersão.
- `/causes/`: Pareto, sunburst, treemap, cruzamentos e tabela.
- `/mortes/`: óbitos — evolução, locais, rodovias, causas e tipos de sinistro.
- `/feridos/`: feridos graves e leves — evolução, gravidade, locais e rodovias.
- `/roads/`: características das vias e segmentos por BR + UF + intervalo quilométrico configurável.
- `/weather/`: condições meteorológicas, iluminação e Sankey de contagens reais.
- `/paraiba/`: recorte PB obrigatório, atalhos de municípios presentes, mapa e tabela.
- `/explorer/`: pesquisa, paginação, ordenação, cruzamentos e comparação de até três categorias.
- `/upload/`: validação, prévia, confirmação de substituição e histórico.

Mais de 65 visualizações, carregadas quando se aproximam da área visível. Os gráficos oferecem zoom e download PNG na barra de ferramentas. CSV e Excel exportam todos os registros filtrados. O PDF apresenta os indicadores, filtros, insights e metodologia (não contém imagens dos gráficos).

Filtros persistem na sessão ao navegar. Trocar UF limpa o município e recarrega suas opções. Na Paraíba, PB é aplicado independentemente do filtro global. Filtros de dimensão, comparação e segmento são específicos da página.

## Dados e metodologia

A base original possui 54.895 registros, 30 colunas, 01/01 a 30/09/2026 e 1.358 registros PB. Esses valores são verificações da versão entregue, não constantes da interface. Testes de referência precisam ser atualizados se o arquivo original for trocado deliberadamente.

`data/datatran2026.csv` não é alterado. `processar_datatran` cria `data/processed/datatran_tratado.csv` e `qualidade.json`. Importações recebidas ficam em `data/raw/`, identificadas por UUID e SHA-256, com histórico SQLite. O dashboard passa a ler `data/processed/active.csv` somente após confirmação explícita. Cada substituição salva um backup. Não existe união automática, mesmo com períodos ou IDs sobrepostos. Para manter a base, basta não confirmar.

- Sinistros = IDs únicos, positivos e inteiros, com data válida. Duplicidades mantêm a primeira linha e são relatadas.
- Óbitos, feridos e veículos = somas dos campos; desconhecidos não são preenchidos com zero. Totais parciais podem existir se houver nulos: consulte a qualidade antes de interpretar.
- Contagens negativas ou fracionárias são anuladas. Decimais com vírgula são convertidos.
- Datas inválidas rejeitam o registro; horário inválido apenas exclui sua participação nas distribuições horárias.
- Coordenadas válidas usam um envelope aproximado do Brasil, sem verificação de fronteiras. Registros sem coordenadas continuam nos indicadores.
- O mapa mostra até 4.000 pontos por amostragem determinística explicitada. Densidade usa os pontos exibidos. KPIs e gráficos usam todo o recorte.
- Categoria desconhecida é identificada nos gráficos aplicáveis. A padronização preserva os significados originais.
- Média diária = sinistros / dias corridos entre primeira e última data do recorte; não normaliza apenas os dias de semana selecionados.
- Variações mensais usam apenas meses consecutivos inteiramente contidos no intervalo observado. Isso não garante completude da coleta na fonte.
- Percentual de feridos graves aparece somente se todos os campos relevantes do recorte forem conhecidos e consistentes.
- Sem denominadores de população, frota ou tráfego; contagens não representam risco relativo. Causas registradas não demonstram causalidade.

## Arquitetura e limites

Serviços em `dashboard/services/` separam limpeza, leitura, filtros, indicadores, gráficos, mapas e insights. Leitura tem cache por caminho/mtime; figuras têm cache de 120 segundos por recorte. SQLite armazena sessões e histórico por ORM, permitindo configuração futura de PostgreSQL. A versão local usa Bootstrap 5 e CSS próprio, Plotly e Leaflet, com arquivos estáticos locais. O fundo do mapa (CARTO, dados OpenStreetMap) exige internet.

Uploads: até 30 MB; ZIP aceita exatamente um CSV, nunca extrai caminhos e limita o tamanho descompactado. XLSX tem expansão limitada a 100 MB. O painel é destinado ao uso local individual em loopback. Antes de expor em rede, configurar autenticação/autorização de importações, segredo por ambiente, DEBUG=False, armazenamento e políticas de implantação. Não há publicação externa nesta entrega.

Verificação automatizada cobre as dez rotas, contagens, filtros, exportações e ativação de upload com backup. Aparência, interação do Plotly e tiles não foram verificados por navegador automatizado nesta sessão.

Arquivos de referência ausentes: `datatran2026 (1).zip`, `PainelPRF (8).zip`, os três guias práticos citados. Não foram criados logotipos oficiais.

## Gráficos para apresentação

A navegação inicia com gráficos simples: barras horizontais e verticais com valores visíveis, linhas, áreas, pizzas e roscas. Rankings mostram até cinco categorias. Pizzas e roscas incluem o total completo, agrupando categorias excedentes em “Demais categorias”. Cada figura apresenta uma medida. As oito páginas temáticas têm seis gráficos cada; os filtros, mapas e exportações continuam usando o recorte completo. As categorias omitidas do ranking são explicitadas na legenda textual, sem alterar os totais dos indicadores.

O botão **Ver gráficos detalhados** recupera heatmaps, treemaps e os demais cruzamentos. A escolha persiste durante a navegação; **Simplificar gráficos** retorna à versão para apresentação.

## Envio ao GitHub

Consulte `GUIA_GITHUB.md`. O pacote inclui o CSV original para permitir executar o painel. Ambiente virtual, banco local, backups e importações não fazem parte da entrega. Configurações locais podem ser definidas por variáveis de ambiente descritas em `.env.example`; o Django não lê esse arquivo automaticamente.

## Layout para apresentação

A interface usa a identidade PMPB em azul-marinho, branco e detalhes vermelhos. Filtros ficam acima dos indicadores e dos gráficos; a seleção ativa aparece em etiquetas. Os seis indicadores da versão atual permanecem exclusivos da Visão Geral.

O botão **Apresentar** oculta o menu lateral para ampliar a área útil. Cada gráfico tem um botão **Ampliar gráfico** no canto superior direito; pressione **Escape** para voltar. Tema claro/escuro, navegação móvel e filtros persistentes continuam disponíveis.

## Arquivo HTML independente

`dashboard.html` é uma versão de apresentação das nove abas, com dados e bibliotecas incorporados. Pode ser aberto diretamente no navegador, sem iniciar Django. Navegação, gráficos, zoom, tema e modo de apresentação funcionam no arquivo. Os fundos dos mapas precisam de internet; os pontos e agregações estão incorporados.

Os dados incorporados representam a base tratada no momento da exportação, com PB aplicado na aba Paraíba em foco. Contagens desconhecidas são preservadas como ausentes nos cálculos locais. Na Visão Geral do HTML, UF, município, BR, mês, período e filtros avançados atualizam os cartões e os quatro gráficos diretamente no navegador. Município, BR, delegacia e UOP respeitam a UF selecionada. A seleção é mantida ao navegar entre abas; as demais abas continuam com o recorte fixo completo ou PB. Exportações CSV/Excel e consulta completa dos registros continuam na aplicação Django. As tabelas do HTML são prévias de até 30 registros. O botão Imprimir página permite imprimir ou salvar a aba em PDF pelo navegador.

Para atualizar o arquivo após alterar a base ou o layout:

```bash
venv/bin/python manage.py exportar_html
```
