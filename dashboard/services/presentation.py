"""Gráficos para apresentação: uma pergunta e uma medida por figura."""
import json
import plotly.graph_objects as go
import plotly.express as px
from .charts import DAYS

LABELS = {'uf':'Estado', 'municipio':'Município', 'br':'Rodovia BR', 'causa_acidente':'Causa registrada', 'tipo_acidente':'Tipo de sinistro', 'classificacao_acidente':'Classificação', 'fase_dia':'Fase do dia', 'tipo_pista':'Tipo de pista', 'tracado_via':'Traçado da via', 'sentido_via':'Sentido de circulação', 'uso_solo':'Uso do solo', 'condicao_metereologica':'Condição meteorológica'}
METRICS = {'sinistros':'Sinistros', 'mortos':'Óbitos', 'feridos':'Feridos', 'feridos_graves':'Feridos graves', 'feridos_leves':'Feridos leves'}
MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']


def charts(df,page,dimension='uf',compare=None):
    if df.empty:
        return []
    figures=[]
    def aggregate(by,metric):
        groups=df.groupby(by,dropna=False)
        return (groups.id.nunique() if metric=='sinistros' else groups[metric].sum(min_count=1)).dropna()
    def add(title,fig,note,metric,horizontal=False):
        color='#ae3443' if metric=='mortos' else '#344b65'
        fig.update_layout(template='plotly_white',height=290,margin=dict(l=12,r=48,t=44,b=24),
                          font=dict(family='system-ui',size=13,color='#536172'),
                          paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                          showlegend=True,separators=',.',bargap=.38,
                          legend=dict(orientation='h',x=1,xanchor='right',y=1.0,yanchor='bottom',font=dict(size=12),bgcolor='rgba(0,0,0,0)'))
        axis_title=dict(font=dict(size=12),standoff=8)
        fig.update_xaxes(automargin=True,showgrid=False,zeroline=False,title=axis_title)
        fig.update_yaxes(automargin=True,showgrid=not horizontal,gridcolor='#e7ebef',zeroline=False,title=axis_title)
        fig.update_traces(marker_color=color,selector=dict(type='bar'))
        fig.update_traces(texttemplate='%{x:,.0f}' if horizontal else '%{y:,.0f}',textposition='outside',cliponaxis=False,selector=dict(type='bar'))
        fig.update_traces(line=dict(color=color,width=3),marker=dict(size=7),selector=dict(type='scatter',mode='lines+markers'))
        fig.update_traces(name=METRICS.get(metric,metric),showlegend=True,selector=dict(type='bar'))
        fig.update_traces(name=METRICS.get(metric,metric),showlegend=True,selector=dict(type='scatter'))
        if horizontal:fig.update_xaxes(rangemode='tozero',showticklabels=False)
        else:fig.update_yaxes(rangemode='tozero')
        figures.append({'title':title,'note':note,'figure':json.loads(fig.to_json())})
    def rank(column,title,metric='sinistros',vertical=False):
        g=aggregate(column,metric).rename_axis('categoria').reset_index(name='valor')
        g['categoria']=g.categoria.astype('string').fillna('Não informado')
        if column=='br':g['categoria']='BR '+g.categoria.str.removesuffix('.0')
        g=g.sort_values('valor',ascending=False).head(5).sort_values('valor')
        if vertical:
            g=g.sort_values('valor',ascending=False)
            g['rotulo']=[wrap(v,14) for v in g.categoria]
            fig=px.bar(g,x='rotulo',y='valor',custom_data=['categoria'],labels={'valor':METRICS[metric],'rotulo':LABELS.get(column,column)})
            fig.update_traces(hovertemplate=LABELS.get(column,column)+'=%{customdata[0]}<br>'+METRICS[metric]+'=%{y:,.0f}<extra></extra>')
            fig.update_xaxes(type='category',tickangle=0,tickfont=dict(size=11))
            add(title,fig,f'{METRICS[metric]} · até 5 categorias com maiores contagens'+('.' if column=='uf' else '; demais categorias não exibidas.'),metric)
            if column!='uf':figures[-1]['figure']['layout']['margin']['r']=12
            return
        fig=px.bar(g,x='valor',y='categoria',orientation='h',labels={'valor':METRICS[metric],'categoria':LABELS.get(column,column)})
        fig.update_yaxes(tickmode='array',tickvals=g.categoria,ticktext=[str(v) if len(str(v))<=36 else str(v)[:33]+'…' for v in g.categoria])
        add(title,fig,f'{METRICS[metric]} · até 5 categorias com maiores contagens; demais categorias não exibidas.',metric,True)
    def share(column,title,hole=0):
        g=aggregate(column,'sinistros').sort_values(ascending=False)
        labels=[str(v) if str(v)!='<NA>' else 'Não informado' for v in g.index[:4]]
        values=[int(v) for v in g.iloc[:4]]
        if len(g)>4:
            labels.append('Demais categorias');values.append(int(g.iloc[4:].sum()))
        if not values or sum(values)==0:
            return
        display=[v if len(v)<=32 else v[:29]+'…' for v in labels]
        fig=go.Figure(go.Pie(labels=display,values=values,customdata=labels,hole=hole,
                            sort=False,textinfo='percent',textposition='inside',
                            hovertemplate='%{customdata}<br>%{value:,.0f} sinistros (%{percent})<extra></extra>',
                            marker=dict(colors=['#344b65','#ba4653','#508b84','#b49b62','#b6bdc7'],line=dict(color='#ffffff',width=2))))
        add(title,fig,'Participação no total de sinistros · todas as categorias incluídas; excedentes agrupadas.','sinistros')
        figures[-1]['figure']['layout'].update(showlegend=True,height=320,
            legend=dict(orientation='h',x=0,y=-.08,font=dict(size=11)),
            margin=dict(l=10,r=10,t=12,b=16))
    def monthly(metric,title,style='line'):

        g=aggregate('mes',metric).rename_axis('mes').reset_index(name='valor').sort_values('mes')
        fig=(px.area if style=='area' else px.line)(g,x='mes',y='valor',markers=True,labels={'valor':METRICS[metric],'mes':'Mês'})
        fig.update_xaxes(type='category',tickmode='array',tickvals=g.mes,ticktext=[f'{MONTHS[int(v[5:7])-1]}/{v[2:4]}' for v in g.mes])
        add(title,fig,f'{METRICS[metric]} por mês · apenas os meses presentes no recorte.',metric)
    def weekdays(metric='sinistros'):
        g=aggregate('semana',metric).sort_index().rename_axis('dia').reset_index(name='valor')
        g['dia']=g.dia.map(lambda n:DAYS[int(n)])
        add('Em quais dias há mais '+{'mortos':'óbitos?','feridos':'feridos?','feridos_graves':'feridos graves?','feridos_leves':'feridos leves?'}.get(metric,'sinistros?'),px.bar(g,x='dia',y='valor',labels={'dia':'Dia da semana','valor':METRICS[metric]}),f'{METRICS[metric]} por dia da semana · contagens absolutas.',metric)
    def severity_split():
        graves,leves=df.feridos_graves.sum(min_count=1),df.feridos_leves.sum(min_count=1)
        values=[0 if v!=v else int(v) for v in (graves,leves)]
        if sum(values)==0:
            return
        fig=go.Figure(go.Pie(labels=['Feridos graves','Feridos leves'],values=values,hole=.55,sort=False,
                            textinfo='percent',textposition='inside',
                            hovertemplate='%{label}<br>%{value:,.0f} pessoas (%{percent})<extra></extra>',
                            marker=dict(colors=['#ae3443','#344b65'],line=dict(color='#ffffff',width=2))))
        add('Gravidade dos feridos',fig,'Feridos graves e leves · soma dos campos de cada registro.','feridos')
        figures[-1]['figure']['layout'].update(showlegend=True,height=320,
            legend=dict(orientation='h',x=0,y=-.08,font=dict(size=11)),margin=dict(l=10,r=10,t=12,b=16))
    def wrap(text,width=16,lines=3):
        words,out,line=str(text).split(),[],''
        for w in words:
            if line and len(line)+1+len(w)>width:out.append(line);line=w
            else:line=(line+' '+w).strip()
        out.append(line)
        if len(out)>lines:out=out[:lines];out[-1]=out[-1][:width-1]+'…'
        return '<br>'.join(out)
    PALETTE=['#344b65','#ba4653','#508b84','#b49b62','#b6bdc7','#7f97b2','#dd9aa1','#8fb8b2','#d6c597']
    PHASES={'Amanhecer':'#dd9aa1','Pleno dia':'#b49b62','Anoitecer':'#ae3443','Plena Noite':'#1f3047'}
    REDS=['#5e1620','#7d1f2b','#ae3443','#c9616d','#dd9aa1'];BLUES=['#1f3047','#344b65','#55708f','#7f97b2','#aebdd0']
    def name_of(column,v):
        v=str(v)
        if v in ('<NA>','nan','None'):return 'Não informado'
        return 'BR '+v.removesuffix('.0') if column=='br' else v
    def top(column,metric,n=5):
        g=aggregate(column,metric).sort_values(ascending=False)
        g=g[g>0].head(n)
        return [name_of(column,v) for v in g.index],[int(v) for v in g]
    def pie(labels,values,title,note,metric,hole=.55,unit='sinistros',colors=None,legend_side=False):
        if not values or sum(values)==0:return
        display=[v if len(v)<=32 else v[:29]+'…' for v in labels]
        fig=go.Figure(go.Pie(labels=display,values=values,customdata=labels,hole=hole,sort=False,direction='clockwise',textinfo='percent',textposition='inside',
                            insidetextorientation='horizontal',hovertemplate='%{customdata}<br>%{value:,.0f} '+unit+' (%{percent})<extra></extra>',
                            marker=dict(colors=colors or PALETTE,line=dict(color='#ffffff',width=2))))
        add(title,fig,note,metric)
        legend=dict(orientation='v',x=1.02,y=.5,font=dict(size=11)) if legend_side else dict(orientation='h',x=0,y=-.08,font=dict(size=11))
        figures[-1]['figure']['layout'].update(showlegend=True,height=320,legend=legend,margin=dict(l=10,r=10,t=12,b=12 if legend_side else 16))
    def share_metric(column,title,metric,note=None,hole=.55,top_n=4):
        g=aggregate(column,metric).sort_values(ascending=False)
        g=g[g>0]
        names=[name_of(column,v) for v in g.index]
        labels,values=names[:top_n],[int(v) for v in g.iloc[:top_n]]
        if len(g)>top_n:labels.append('Demais');values.append(int(g.iloc[top_n:].sum()))
        colors=[PHASES.get(l,PALETTE[i%len(PALETTE)]) for i,l in enumerate(labels)] if column=='fase_dia' else None
        pie(labels,values,title,note or f'{METRICS[metric]} · participação de cada categoria; demais agrupadas.',metric,hole,METRICS[metric].lower(),colors)
    def treemap(column,title,metric,note):
        names,vals=top(column,metric)
        if not vals:return
        colors=(REDS if metric=='mortos' else BLUES)[:len(vals)]
        fig=go.Figure(go.Treemap(labels=[wrap(n,22,3) for n in names],parents=['']*len(names),values=vals,customdata=names,branchvalues='total',sort=True,
                                 marker=dict(colors=colors,line=dict(color='#ffffff',width=2),pad=dict(t=2,l=2,r=2,b=2)),
                                 textinfo='label+value',texttemplate='<b>%{value:,.0f}</b><br>%{label}',textfont=dict(color='#ffffff',size=12),textposition='middle center',
                                 hovertemplate='%{customdata}<br>%{value:,.0f} '+METRICS[metric].lower()+' (%{percentRoot:.1%} entre os '+str(len(vals))+')<extra></extra>',
                                 tiling=dict(packing='squarify',pad=3)))
        add(title,fig,note,metric)
        swatch='#7d1f2b' if metric=='mortos' else '#344b65'
        figures[-1]['figure']['layout'].update(height=320,showlegend=False,margin=dict(l=6,r=6,t=30,b=8),
            annotations=[dict(xref='paper',yref='paper',x=1,y=1.0,xanchor='right',yanchor='bottom',showarrow=False,align='right',font=dict(size=12),
                              text=f'<span style="color:{swatch}">■</span> {METRICS[metric]} · tamanho do bloco = quantidade')])
    def polar_layout(rmax,angle):
        return dict(bgcolor='rgba(0,0,0,0)',radialaxis=dict(visible=True,rangemode='tozero',gridcolor='#e7ebef',linecolor='#e7ebef',tickfont=dict(size=9),
                    angle=angle,tickangle=angle,nticks=4,range=[0,rmax*1.1]),angularaxis=dict(direction='clockwise',rotation=90,gridcolor='#e7ebef',linecolor='#c9d2dc'))
    def radar_weekdays(metric):
        g=aggregate('semana',metric).sort_index()
        days=[DAYS[int(n)] for n in g.index];vals=[int(v) for v in g]
        if not vals:return
        color='#ae3443' if metric=='mortos' else '#344b65'
        fig=go.Figure(go.Scatterpolar(r=vals+vals[:1],theta=days+days[:1],mode='lines+markers',fill='toself',fillcolor='rgba(174,52,67,0.22)' if metric=='mortos' else 'rgba(52,75,101,0.22)',
                                      line=dict(color=color,width=3),marker=dict(size=7,color=color),name=METRICS[metric],showlegend=True,
                                      hovertemplate='Dia=%{theta}<br>'+METRICS[metric]+'=%{r:,.0f}<extra></extra>'))
        add('Em quais dias há mais '+('óbitos?' if metric=='mortos' else 'sinistros?'),fig,f'{METRICS[metric]} por dia da semana · quanto mais longe do centro, mais {"óbitos" if metric=="mortos" else "sinistros"}.',metric)
        figures[-1]['figure']['layout'].update(height=320,showlegend=True,margin=dict(l=40,r=40,t=40,b=24),polar=polar_layout(max(vals),64),
            legend=dict(orientation='h',x=0,xanchor='left',y=1.0,yanchor='bottom',font=dict(size=12),bgcolor='rgba(0,0,0,0)'))
    def phases_polar(metric,title,note):
        g=aggregate('fase_dia',metric)
        order=[p for p in PHASES if p in g.index]
        if not order:return
        fig=go.Figure([go.Barpolar(r=[int(g[p])],theta=[p],name=p,marker=dict(color=PHASES[p],line=dict(color='#ffffff',width=2)),
                                   hovertemplate=p+'<br>%{r:,.0f} '+METRICS[metric].lower()+'<extra></extra>') for p in order])
        add(title,fig,note,metric)
        figures[-1]['figure']['layout'].pop('legend',None);figures[-1]['figure']['layout'].pop('showlegend',None)
        figures[-1]['figure']['layout'].update(height=320,margin=dict(l=40,r=40,t=40,b=24),
            polar={**polar_layout(max(float(g[p]) for p in order),45),'hole':.08})
    def lollipop(column,title,metric,note=None):
        names,vals=top(column,metric)
        if not vals:return
        color='#ae3443' if metric=='mortos' else '#344b65';label=LABELS.get(column,column)
        fig=go.Figure(go.Scatter(x=vals,y=names,mode='markers+text',marker=dict(color=color,size=16,line=dict(color='#ffffff',width=2)),
                                 text=[f'{v:,}'.replace(',','.') for v in vals],textposition='middle right',textfont=dict(size=12),cliponaxis=False,
                                 hovertemplate=label+'=%{y}<br>'+METRICS[metric]+'=%{x:,.0f}<extra></extra>'))
        add(title,fig,note or f'{METRICS[metric]} · até 5 categorias com maiores contagens; demais categorias não exibidas.',metric)
        lay=figures[-1]['figure']['layout']
        lay['xaxis'].update(showgrid=True,gridcolor='#e7ebef',rangemode='tozero',range=[0,max(vals)*1.18],title={'text':METRICS[metric],'font':{'size':12},'standoff':8})
        lay['yaxis'].update(showgrid=False,type='category',autorange='reversed',title={'text':label,'font':{'size':12},'standoff':8})
        lay['shapes']=[dict(type='line',xref='x',yref='y',x0=0,x1=v,y0=n,y1=n,line=dict(color=color,width=3),layer='below') for n,v in zip(names,vals)]
    def monthly_hbar(metric,title):
        g=aggregate('mes',metric).rename_axis('mes').reset_index(name='valor').sort_values('mes')
        g['rotulo']=[f'{MONTHS[int(v[5:7])-1]}/{v[2:4]}' for v in g.mes]
        fig=px.bar(g,x='valor',y='rotulo',orientation='h',labels={'valor':METRICS[metric],'rotulo':'Mês'})
        add(title,fig,f'{METRICS[metric]} por mês · barras horizontais, de janeiro (topo) ao último mês do recorte.',metric,True)
        lay=figures[-1]['figure']['layout'];lay['bargap']=.32;lay['yaxis'].update(type='category',autorange='reversed',showgrid=False)
    def monthly_pie(metric,title):
        g=aggregate('mes',metric).sort_index()
        g=g[g>0]
        pie([f'{MONTHS[int(v[5:7])-1]}/{v[2:4]}' for v in g.index],[int(v) for v in g],title,f'Participação de cada mês no total de {METRICS[metric].lower()} do recorte.',metric,hole=0,unit=METRICS[metric].lower(),legend_side=True)
    if page=='overview':
        monthly('sinistros','Sinistros ao longo dos meses',style='area')
        rank('uf','5 estados com mais sinistros',vertical=True)
        share('classificacao_acidente','Como os sinistros são classificados?',hole=.55)
        rank('causa_acidente','5 causas mais registradas')
    elif page=='temporal':
        monthly('sinistros','Sinistros por mês');monthly_hbar('mortos','Óbitos por mês')
        monthly_pie('feridos_leves','Feridos leves por mês');weekdays()
    elif page in ['geographic','paraiba']:
        if page=='geographic':
            rank('uf','5 estados com mais sinistros',vertical=True);rank('municipio','5 municípios com mais sinistros');share('br','Participação das rodovias nos sinistros')
        else:
            monthly('sinistros','Sinistros na Paraíba por mês');rank('municipio','5 municípios com mais sinistros',vertical=True)
            share('br','Participação das rodovias nos sinistros');lollipop('municipio','5 municípios com mais óbitos','mortos')
    elif page=='causes':
        rank('causa_acidente','5 causas mais registradas');rank('tipo_acidente','5 tipos de sinistro mais frequentes',vertical=True)
        treemap('causa_acidente','5 causas com mais óbitos registrados','mortos','Óbitos · área de cada bloco proporcional às mortes entre as 5 principais causas.')
        rank('tipo_acidente','5 tipos de sinistro com mais óbitos','mortos',vertical=True)
    elif page=='mortes':
        radar_weekdays('mortos');lollipop('municipio','5 municípios com mais óbitos','mortos')
        treemap('br','5 rodovias com mais óbitos','mortos','Óbitos · área de cada bloco proporcional às mortes entre as 5 rodovias.')
        share_metric('fase_dia','Óbitos por fase do dia','mortos','Participação de cada fase do dia no total de óbitos.')
    elif page=='feridos':
        monthly('feridos','Feridos por mês',style='area');severity_split()
        rank('uf','5 estados com mais feridos','feridos',vertical=True);rank('tipo_acidente','5 tipos de sinistro com mais feridos graves','feridos_graves')
    elif page=='roads':
        rank('br','5 rodovias com mais sinistros');share('tipo_pista','Sinistros por tipo de pista',hole=.55);rank('tracado_via','5 traçados com mais registros',vertical=True)
    elif page=='weather':
        rank('condicao_metereologica','5 condições meteorológicas mais registradas',vertical=True);lollipop('condicao_metereologica','Óbitos por condição meteorológica','mortos')
        phases_polar('mortos','Óbitos por fase do dia','Óbitos · cada fatia avança do amanhecer à noite; quanto maior a fatia, mais óbitos.')
        treemap('condicao_metereologica','Feridos graves por condição meteorológica','feridos_graves','Feridos graves · área de cada bloco proporcional entre as 5 condições mais registradas.')
    elif page=='explorer':
        rank(dimension,'Categorias com mais sinistros');rank(dimension,'Categorias com mais óbitos','mortos')
        if compare:
            sub=df.loc[df[dimension].isin(compare)].groupby(['mes',dimension]).id.nunique().reset_index(name='sinistros')
            fig=px.line(sub,x='mes',y='sinistros',color=dimension,markers=True,labels={'mes':'Mês','sinistros':'Sinistros',dimension:LABELS.get(dimension,dimension)})
            add('Comparação ao longo dos meses',fig,'Sinistros por mês nas categorias selecionadas.','sinistros')
            figures[-1]['figure']['layout']['showlegend']=True
    return figures
