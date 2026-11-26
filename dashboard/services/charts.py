"""Figuras declarativas compartilhadas; apenas agregações de registros únicos."""
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LABELS = {'uf':'UF','municipio':'Município','br':'BR','mortos':'Óbitos','feridos':'Feridos','n':'Sinistros','mes':'Mês','hora':'Hora','semana':'Dia da semana'}
DAYS = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']


def charts(df, page, segment=10, dimension='uf', measure='mortos', compare=None):
    if df.empty:
        return []
    figures=[]
    def add(title, fig, note='Contagens absolutas no recorte selecionado.'):
        fig.update_layout(template='plotly_white',height=355,margin=dict(l=35,r=25,t=20,b=45),font=dict(family='system-ui',size=12,color='#64748b'),colorway=['#2376df','#14a5a0','#e36a76','#a693d0','#e5b45a'],paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',separators=',.',legend=dict(orientation='h',y=-.25),hovermode='closest')
        if page == 'overview':
            fig.update_layout(height=280, margin=dict(l=30,r=18,t=10,b=34),
                              font=dict(size=11), colorway=['#34475d','#b63846','#4e8b87','#aa955e','#8e7da2'],
                              legend=dict(orientation='h',y=-.22,font=dict(size=10)))
            fig.update_xaxes(automargin=True,showgrid=False,zeroline=False)
            fig.update_yaxes(automargin=True,gridcolor='#e9edf1',zeroline=False)
            fig.update_traces(marker_line_width=0,selector=dict(type='bar'))
            fig.update_traces(textinfo='percent',textfont_size=11,selector=dict(type='pie'))
        figures.append({'title':title,'note':note,'figure':json.loads(fig.to_json())})
    def rank(c,title,metric=None):
        g = df.groupby(c,dropna=False)[metric].sum(min_count=1).dropna().nlargest(10) if metric else df[c].fillna('Não informado').value_counts().head(10)
        g = g.sort_values().rename_axis(c).reset_index(name='valor')
        g[c]=g[c].astype(str)
        add(title,px.bar(g,x='valor',y=c,orientation='h',labels={'valor':LABELS.get(metric,'Sinistros'),c:LABELS.get(c,c)}))
    def heat(a,b,title,metric=None):
        g = df.pivot_table(index=a,columns=b,values=metric or 'id',aggfunc='sum' if metric else 'count',fill_value=0)
        add(title,px.imshow(g.to_numpy(),x=[str(x) for x in g.columns],y=[DAYS[int(x)] if a=='semana' else str(x) for x in g.index],aspect='auto',color_continuous_scale='Blues',labels={'color':LABELS.get(metric,'Sinistros'),'x':LABELS.get(b,b),'y':LABELS.get(a,a)}))
    def tree(path,title,metric=None,kind='tree'):
        base=df.copy()
        for c in path:
            base[c]=base[c].fillna('Não informado').astype(str)
        g=base.groupby(path,dropna=False).agg(valor=(metric or 'id','sum' if metric else 'count')).reset_index()
        g=g.loc[g.valor>0]
        if len(g):
            add(title,(px.sunburst if kind=='sun' else px.treemap)(g,path=path,values='valor',color='valor',color_continuous_scale='Blues'))
    def stacked(c,title,metrics):
        g=df.groupby(c)[metrics].sum(min_count=1).reset_index()
        add(title,px.bar(g,x=c,y=metrics,barmode='stack',labels=LABELS))
    monthly=df.groupby('mes').agg(n=('id','nunique'),mortos=('mortos',lambda s:s.sum(min_count=1)),feridos=('feridos',lambda s:s.sum(min_count=1)),feridos_graves=('feridos_graves',lambda s:s.sum(min_count=1)),feridos_leves=('feridos_leves',lambda s:s.sum(min_count=1))).reset_index()
    def timeline(title,metrics,area=False):
        add(title,(px.area if area else px.line)(monthly,x='mes',y=metrics,labels=LABELS))
    if page=='overview':
        timeline('Evolução mensal dos sinistros',['n'],True)
        fig=make_subplots(specs=[[{'secondary_y':True}]])
        fig.add_trace(go.Bar(x=monthly.mes,y=monthly.n,name='Sinistros'))
        fig.add_trace(go.Scatter(x=monthly.mes,y=monthly.mortos,name='Óbitos'),secondary_y=True)
        fig.update_yaxes(title_text='Sinistros',secondary_y=False);fig.update_yaxes(title_text='Óbitos',secondary_y=True)
        add('Sinistros e óbitos por mês',fig)
        rank('uf','Estados com mais sinistros')
        g=df.classificacao_acidente.fillna('Não informado').value_counts().reset_index();g.columns=['classe','n']
        add('Classificação dos sinistros',px.pie(g,names='classe',values='n',hole=.7))
        heat('semana','hora','Concentração por dia e hora')
        tree(['causa_acidente'],'Principais causas registradas')
        rank('fase_dia','Sinistros por fase do dia')
        add('Sinistros com e sem óbitos',px.bar(x=['Com óbitos','Sem óbitos conhecidos','Óbitos não informados'],y=[int(df.mortos.gt(0).sum()),int(df.mortos.eq(0).sum()),int(df.mortos.isna().sum())],labels={'x':'Situação','y':'Sinistros'}))
    elif page=='temporal':
        timeline('Evolução mensal dos sinistros',['n'],True);timeline('Evolução mensal de óbitos',['mortos']);timeline('Evolução de feridos',['feridos_graves','feridos_leves'])
        heat('mes','semana','Mês e dia da semana');heat('semana','hora','Dia da semana e hora')
        g=df.hora.value_counts().sort_index()
        add('Distribuição das ocorrências por hora',go.Figure(go.Scatterpolar(r=g.values,theta=g.index.astype(str),fill='toself')))
        daily=df.groupby('data_inversa').id.nunique().reindex(pd.date_range(df.data_inversa.min(),df.data_inversa.max()),fill_value=0)
        cal=pd.DataFrame({'data':daily.index,'n':daily.values});cal['dia']=cal.data.dt.day;cal['mes']=cal.data.dt.strftime('%Y-%m')
        add('Calendário de ocorrências diárias',px.density_heatmap(cal,x='dia',y='mes',z='n',histfunc='sum',nbinsx=31,color_continuous_scale='Blues',labels={'dia':'Dia do mês','mes':'Mês','n':'Sinistros'}))
        rank('hora','Horários mais frequentes')
        add('Dias úteis e finais de semana',px.bar(x=['Dias úteis','Fim de semana'],y=[int((df.semana<5).sum()),int((df.semana>=5).sum())],labels={'x':'Grupo','y':'Sinistros'}),'Contagens brutas: os grupos têm quantidades diferentes de dias.')
        # Apenas meses integralmente cobertos no recorte.
        first,last=df.data_inversa.min(),df.data_inversa.max()
        full=monthly.loc[(pd.to_datetime(monthly.mes)>=first)&((pd.to_datetime(monthly.mes)+pd.offsets.MonthEnd(0))<=last)].copy()
        full['variacao']=full.n.pct_change(fill_method=None)*100
        consecutive=pd.to_datetime(full.mes).dt.to_period('M').astype('int64').diff().eq(1)
        full.loc[~consecutive,'variacao']=np.nan
        full=full.dropna(subset=['variacao'])
        if len(full):add('Variação mensal em meses completos',px.bar(full,x='mes',y='variacao',labels={'variacao':'Variação (%)','mes':'Mês'}),'Meses com cobertura integral do intervalo; lacunas de meses não são comparadas.')
    elif page in ['geographic','paraiba']:
        rank('municipio','Municípios com mais sinistros');rank('br','Rodovias com mais sinistros')
        if page=='geographic':
            rank('uf','Ranking de UFs');stacked('uf','Vítimas por UF',['mortos','feridos']);tree(['uf','municipio'],'UF e município')
        else:
            timeline('Evolução mensal na Paraíba',['n'],True);heat('semana','hora','Dia e horário na Paraíba');rank('causa_acidente','Causas registradas na Paraíba');rank('tipo_acidente','Tipos de sinistros');stacked('municipio','Vítimas por município',['mortos','feridos_graves','feridos_leves'])
        g=df.groupby(['uf','municipio']).agg(n=('id','nunique'),mortos=('mortos','sum')).reset_index()
        add('Volume e gravidade municipal',px.scatter(g,x='n',y='mortos',hover_name='municipio',color='uf',labels=LABELS))
    elif page=='causes':
        rank('causa_acidente','Causas mais frequentes');tree(['causa_acidente'],'Participação das causas');tree(['causa_acidente','tipo_acidente'],'Causa e tipo de sinistro',kind='sun')
        g=df.groupby(['tipo_acidente','classificacao_acidente'],dropna=False).size().reset_index(name='n')
        add('Tipos e classificação',px.bar(g.fillna('Não informado'),x='tipo_acidente',y='n',color='classificacao_acidente',labels=LABELS))
        g=df.causa_acidente.value_counts().reset_index();g.columns=['causa','n'];g['acumulado']=g.n.cumsum()/g.n.sum()*100
        fig=make_subplots(specs=[[{'secondary_y':True}]]);fig.add_trace(go.Bar(x=g.causa,y=g.n,name='Sinistros'));fig.add_trace(go.Scatter(x=g.causa,y=g.acumulado,name='Acumulado (%)'),secondary_y=True);fig.update_yaxes(title_text='Acumulado (%)',secondary_y=True)
        add('Pareto das causas registradas',fig)
        top=df.causa_acidente.value_counts().head(10).index
        sub=df.loc[df.causa_acidente.isin(top)]
        g=sub.pivot_table(index='causa_acidente',columns='tipo_acidente',values='id',aggfunc='count',fill_value=0)
        add('Causa e tipo: dez causas mais frequentes',px.imshow(g,aspect='auto',color_continuous_scale='Blues'))
        rank('tipo_acidente','Tipos com mais óbitos','mortos');rank('causa_acidente','Óbitos segundo causa registrada','mortos')
        g=sub.groupby(['mes','causa_acidente']).size().reset_index(name='n');add('Evolução das principais causas',px.line(g,x='mes',y='n',color='causa_acidente',labels=LABELS))
    elif page=='mortes':
        timeline('Evolução mensal de óbitos',['mortos']);rank('uf','UFs com mais óbitos','mortos')
        rank('municipio','Municípios com mais óbitos','mortos');rank('br','Rodovias com mais óbitos','mortos')
        tree(['tipo_acidente'],'Tipos de sinistro e óbitos','mortos');rank('causa_acidente','Causas registradas com mais óbitos','mortos')
        heat('semana','hora','Óbitos por dia e horário','mortos');stacked('condicao_metereologica','Óbitos por meteorologia',['mortos'])
        g=df.groupby(['uf','municipio']).agg(n=('id','nunique'),mortos=('mortos','sum')).reset_index();add('Sinistros e óbitos por município',px.scatter(g,x='n',y='mortos',hover_name='municipio',labels=LABELS))
        add('Sinistros com e sem óbitos',px.bar(x=['Com óbitos','Sem óbitos conhecidos','Óbitos não informados'],y=[int(df.mortos.gt(0).sum()),int(df.mortos.eq(0).sum()),int(df.mortos.isna().sum())],labels={'x':'Situação','y':'Sinistros'}))
    elif page=='feridos':
        timeline('Evolução mensal de feridos graves e leves',['feridos_graves','feridos_leves']);stacked('uf','Feridos graves e leves por UF',['feridos_graves','feridos_leves'])
        rank('municipio','Municípios com mais feridos','feridos');rank('br','Rodovias com mais feridos','feridos')
        tree(['tipo_acidente'],'Tipos de sinistro e feridos graves','feridos_graves');rank('causa_acidente','Causas registradas com mais feridos graves','feridos_graves')
        heat('semana','hora','Feridos por dia e horário','feridos');stacked('condicao_metereologica','Feridos por meteorologia',['feridos_graves','feridos_leves'])
        add('Distribuição de feridos por sinistro',px.box(df,y='feridos',points=False,labels=LABELS))
        g=df.groupby(['uf','municipio']).agg(n=('id','nunique'),feridos=('feridos','sum')).reset_index();add('Sinistros e feridos por município',px.scatter(g,x='n',y='feridos',hover_name='municipio',labels=LABELS))
    elif page=='roads':
        rank('br','Rodovias com mais sinistros');rank('tipo_pista','Tipo de pista');rank('tracado_via','Traçado da via');rank('sentido_via','Sentido de circulação');rank('uso_solo','Uso do solo');stacked('tipo_pista','Gravidade por tipo de pista',['mortos','feridos_graves','feridos_leves']);heat('br','tipo_acidente','Rodovia e tipo de sinistro');tree(['br','municipio'],'Rodovia e município')
        g=segments(df,segment).head(15)
        add('Segmentos com maior concentração',px.bar(g,x='segmento',y='sinistros',labels={'segmento':'BR / UF / km','sinistros':'Sinistros'}),f'Faixas de {segment} km, separadas por BR e UF; sem ajuste por exposição ao tráfego.')
    elif page=='weather':
        rank('condicao_metereologica','Condição meteorológica');rank('fase_dia','Fase do dia');stacked('condicao_metereologica','Óbitos por meteorologia',['mortos']);heat('mes','condicao_metereologica','Mês e meteorologia');stacked('condicao_metereologica','Gravidade segundo meteorologia',['mortos','feridos_graves','feridos_leves'])
        g=df.groupby(['mes','fase_dia'],dropna=False).size().reset_index(name='n');add('Fase do dia ao longo dos meses',px.area(g.fillna('Não informado'),x='mes',y='n',color='fase_dia',labels=LABELS))
        rank('fase_dia','Óbitos por fase do dia','mortos')
        periods=df.fase_dia.map({'Pleno dia':'Diurno','Plena Noite':'Noturno','Plena noite':'Noturno','Amanhecer':'Transição','Anoitecer':'Transição'}).fillna('Não informado / outra categoria')
        g=periods.value_counts().rename_axis('periodo').reset_index(name='n')
        add('Períodos diurnos, noturnos e de transição',px.bar(g,x='periodo',y='n',labels={'periodo':'Período','n':'Sinistros'}),'Amanhecer e anoitecer são apresentados como transição; não há ajuste pela duração dos períodos.')
        columns=['condicao_metereologica','fase_dia','classificacao_acidente'];base=df[columns].fillna('Não informado');nodes=[];links=[]
        for i,c in enumerate(columns):nodes.extend((i,str(v)) for v in base[c].unique())
        lookup={node:i for i,node in enumerate(nodes)}
        for i in range(2):
            grouped=base.groupby(columns[i:i+2]).size()
            links.extend((lookup[(i,str(a))],lookup[(i+1,str(b))],int(v)) for (a,b),v in grouped.items())
        add('Meteorologia → fase do dia → classificação',go.Figure(go.Sankey(node={'label':[v for _,v in nodes],'pad':12},link={'source':[a for a,b,v in links],'target':[b for a,b,v in links],'value':[v for a,b,v in links]})))
    elif page=='explorer':
        rank(dimension,'Cruzamento por dimensão selecionada');stacked(dimension,'Vítimas na dimensão selecionada',['mortos','feridos_graves','feridos_leves'])
        if compare:
            g=df.loc[df[dimension].isin(compare)].groupby(['mes',dimension]).size().reset_index(name='n');add('Comparação das localidades selecionadas',px.line(g,x='mes',y='n',color=dimension,labels=LABELS))
    return figures


def segments(df,size=10):
    base=df.loc[df.km.notna() & df.br.notna()].copy()
    start=np.floor(base.km/size)*size
    base['segmento']='BR '+base.br.astype('Int64').astype(str)+' / '+base.uf.fillna('?')+' / '+start.astype('Int64').astype(str)+'–'+(start+size).astype('Int64').astype(str)+' km'
    return base.groupby('segmento').agg(sinistros=('id','nunique'),obitos=('mortos',lambda s:s.sum(min_count=1))).sort_values('sinistros',ascending=False).reset_index()
