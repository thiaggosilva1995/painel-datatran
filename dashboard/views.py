import hashlib
import io
import json
import logging
from pathlib import Path
import shutil
import uuid
import pandas as pd
from django.conf import settings
from django.core.paginator import Paginator
from django.core.cache import cache
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import Importacao
from .forms import UploadForm
from .services.data_loader import load, read_file, _load
from .services.data_cleaning import clean, COLUMNS
from .services.filters import apply, options, FIELDS
from .services.indicators import indicators
from .services.insights import insights
from .services.charts import charts, segments
from .services.presentation import charts as presentation_charts
from .services.maps import map_data

PAGES = [('overview','Visão geral','◫'),('temporal','Análise temporal','◷'),('geographic','Distribuição geográfica','◎'),('causes','Causas e tipologias','⌘'),('mortes','Mortes','✝'),('feridos','Feridos','✚'),('roads','Via e infraestrutura','⇄'),('weather','Clima e visibilidade','☀'),('paraiba','Paraíba em foco','◈'),('explorer','Exploração avançada','⊞'),('upload','Gestão e qualidade','▤')]
# Abas ocultas do menu lateral (continuam acessíveis pelo endereço direto).
HIDDEN = {'explorer','upload'}
NAV = [p for p in PAGES if p[0] not in HIDDEN]
# Indicadores exibidos na Visão geral.
OVERVIEW_KPIS = {'Sinistros registrados','Óbitos','Feridos','Feridos graves','Óbitos / 100 sinistros','UF com mais sinistros'}
NOTES = {'causes':'Causa registrada não demonstra, por si só, causalidade estatística.', 'roads':'Concentração absoluta de sinistros não equivale a risco por quilômetro percorrido. Não há denominadores de tráfego.', 'weather':'Diferenças descritivas não demonstram efeito causal do clima.', 'temporal':'Apenas meses observados são apresentados. Meses parciais não entram na comparação percentual.', 'mortes':'Óbitos somam o campo de mortos de cada registro; quantidades desconhecidas permanecem nulas.', 'feridos':'Feridos somam os campos de feridos graves e leves de cada registro; quantidades desconhecidas permanecem nulas.'}


PAGE_DESCRIPTIONS = {
    'overview': 'Uma visão integrada dos sinistros e do impacto humano nas rodovias federais.',
    'temporal': 'Acompanhe a evolução das ocorrências e os padrões por mês, dia e horário.',
    'geographic': 'Explore a distribuição territorial dos registros e compare localidades.',
    'causes': 'Entenda a distribuição das causas registradas e dos tipos de sinistro.',
    'mortes': 'Analise os óbitos registrados por período, localidade e características do sinistro.',
    'feridos': 'Explore os registros de feridos leves e graves nas rodovias federais.',
    'roads': 'Examine as rodovias e as características dos locais com sinistros registrados.',
    'weather': 'Compare os registros segundo as condições do tempo e de iluminação.',
    'paraiba': 'Um olhar sobre os sinistros nas rodovias federais da Paraíba.',
}


def parameters(request):
    if request.GET.get('limpar'):
        request.session.pop('filters',None)
        return {}
    keys = [*FIELDS,'inicio','fim','hora_inicio','hora_fim','q']
    if 'aplicar' in request.GET:
        params={key:request.GET.get(key,'') for key in keys}
        request.session['filters']=params
        return params
    params=request.session.get('filters',{}).copy()
    params.update({key:request.GET[key] for key in keys if key in request.GET})
    if any(key in request.GET for key in keys):
        request.session['filters']=params
    return params


def index(request, page='overview'):
    if page=='victims':return redirect('/mortes/')
    if page not in dict((p[0],p[1]) for p in PAGES):raise Http404()
    params=parameters(request)
    if request.GET.get('visual') in ['simples','detalhado']:
        request.session['chart_mode']=request.GET['visual']
    chart_mode=request.session.get('chart_mode','simples')
    context={'page_description':PAGE_DESCRIPTIONS.get(page,''),'pages':NAV,'page':page,'title':dict((p[0],p[1]) for p in PAGES)[page],'params':params,'chart_mode':chart_mode,'note':NOTES.get(page,'Contagens absolutas de registros. Não representam taxas de risco por população, frota ou tráfego.')}
    try:
        raw,quality=load()
    except (OSError,ValueError) as exc:
        context.update(error=str(exc),figures=[],kpis=[])
        return render(request,'dashboard/panel.html',context)
    df=apply(raw,params,page=='paraiba')
    context.update(filters=options(raw,params,page=='paraiba'),quality=quality,kpis=[k for k in indicators(df) if k['label'] in OVERVIEW_KPIS],empty=df.empty,period=f'{raw.data_inversa.min():%d/%m/%Y} — {raw.data_inversa.max():%d/%m/%Y}',observed=f'{df.data_inversa.min():%d/%m/%Y} — {df.data_inversa.max():%d/%m/%Y}' if len(df) else 'Sem dados',rows=len(df))
    primary_keys = {'uf', 'municipio', 'br'} | ({'mes'} if page == 'overview' else set())
    context['primary_filters'] = [item for item in context['filters'] if item['key'] in primary_keys]
    context['advanced_filters'] = [item for item in context['filters'] if item['key'] not in primary_keys]
    filter_labels = {**FIELDS, 'inicio': 'Desde', 'fim': 'Até', 'hora_inicio': 'Hora inicial', 'hora_fim': 'Hora final', 'q': 'Pesquisa'}
    context['active_filters'] = [{'label': label, 'value': params[key]} for key, label in filter_labels.items() if params.get(key)]
    if page=='upload':return upload(request,context,raw)
    try:segment=max(1,min(100,int(request.GET.get('segmento','10'))))
    except ValueError:segment=10
    dimension=request.GET.get('dimensao','uf')
    if dimension not in FIELDS:dimension='uf'
    compared=request.GET.getlist('comparar')[:3]
    signature=hashlib.sha256(json.dumps(['presentation-varied-v3',chart_mode,page,params,segment,dimension,compared,raw.id.tolist(),quality],sort_keys=True,default=str).encode()).hexdigest()
    figures=cache.get(signature)
    if figures is None:
        figures=presentation_charts(df,page,dimension,compare=compared) if chart_mode=='simples' else charts(df,page,segment,dimension,compare=compared)
        cache.set(signature,figures,120)
    context.update(figures=figures,dimension=dimension,dimensions=FIELDS,comparison_values=sorted(df[dimension].dropna().astype(str).unique()),compared=compared,segment=segment)
    if page in ['geographic','paraiba']:context['map']=map_data(df)
    if page=='paraiba':
        context['quick_cities']=[city for city in ['JOAO PESSOA','CAMPINA GRANDE','CABEDELO','GUARABIRA'] if city in raw.loc[raw.uf.eq('PB'),'municipio'].values]
        context['pb_stats']={'municípios':df.municipio.nunique(),'rodovia com mais sinistros':str(df.br.mode().iloc[0]) if df.br.notna().any() else 'Sem dados'}
    if page in ['explorer','paraiba','causes']:
        order=request.GET.get('ordem','data_inversa')
        if order.lstrip('-') not in COLUMNS:order='data_inversa'
        records=df.sort_values(order.lstrip('-'),ascending=not order.startswith('-'),na_position='last')[COLUMNS].copy()
        records['data_inversa']=records.data_inversa.dt.strftime('%d/%m/%Y')
        pager=Paginator(records.to_dict('records'),30).get_page(request.GET.get('pagina'))
        context.update(table_columns=COLUMNS,table_rows=[[('—' if pd.isna(row[c]) else row[c]) for c in COLUMNS] for row in pager.object_list],pager=pager,order=order)
        query=request.GET.copy();query.pop('pagina',None);context['table_query']=query.urlencode()
    if page=='roads':context['segments']=segments(df,segment).head(30).to_dict('records')
    return render(request,'dashboard/panel.html',context)


def upload(request,context,raw):
    form=UploadForm(request.POST or None,request.FILES or None)
    preview=None
    if request.method=='POST':
        if request.POST.get('acao')=='ativar':
            import_id=request.session.get('pending_import')
            try:
                with transaction.atomic():
                    item=Importacao.objects.select_for_update().get(pk=import_id,status='prévia')
                    path=Path(item.arquivo)
                    if hashlib.sha256(path.read_bytes()).hexdigest()!=item.sha256:raise ValueError('Integridade do arquivo não confere.')
                    with path.open('rb') as f:new,report=clean(read_file(f,item.nome))
                    if new.empty:raise ValueError('A base não contém registros válidos.')
                    target=settings.BASE_DIR/'data/processed/active.csv'
                    backup=settings.BASE_DIR/'data/raw'/f'backup-{uuid.uuid4().hex}.csv'
                    current=target if target.exists() else settings.BASE_DIR/'data/datatran2026.csv'
                    shutil.copy2(current,backup)
                    temp=target.with_suffix('.tmp')
                    new[COLUMNS].to_csv(temp,index=False,sep=';',encoding='utf-8-sig')
                    temp.replace(target)
                    item.status='ativa';item.save(update_fields=['status'])
                    Importacao.objects.filter(status='ativa').exclude(pk=item.pk).update(status='arquivada')
                _load.cache_clear();request.session.pop('pending_import',None)
                messages.success(request,'Base substituída. Backup preservado; nenhum registro foi unido automaticamente.')
                return redirect('/upload/')
            except (Importacao.DoesNotExist,OSError,ValueError) as exc:messages.error(request,f'Não foi possível ativar: {exc}')
        elif form.is_valid():
            file=form.cleaned_data['arquivo']
            try:
                new,report=clean(read_file(file,file.name))
                if new.empty:raise ValueError('Nenhum registro válido encontrado.')
                file.seek(0);content=file.read()
                path=settings.BASE_DIR/'data/raw'/f'{uuid.uuid4().hex}{Path(file.name).suffix.lower()}'
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
                report['ids_em_comum']=int(new.id.isin(raw.id).sum())
                report['periodos_sobrepostos']=bool(new.data_inversa.min()<=raw.data_inversa.max() and new.data_inversa.max()>=raw.data_inversa.min())
                item=Importacao.objects.create(nome=Path(file.name).name,arquivo=str(path),sha256=hashlib.sha256(content).hexdigest(),relatorio=report)
                request.session['pending_import']=item.pk
                preview=new.head(8)[['id','data_inversa','uf','municipio','mortos']].astype(str).values.tolist()
                context['preview_report']=report
            except Exception as exc:
                logging.getLogger(__name__).warning('Falha de importação: %s',exc)
                form.add_error('arquivo',f'Arquivo não importado: {exc}')
    pending=Importacao.objects.filter(pk=request.session.get('pending_import'),status='prévia').first()
    context.update(form=form,preview=preview,pending=pending,history=Importacao.objects.order_by('-criado')[:20])
    return render(request,'dashboard/panel.html',context)


def export(request,kind):
    raw,_=load();df=apply(raw,parameters(request),request.GET.get('contexto')=='paraiba')
    if kind=='csv':
        response=HttpResponse(content_type='text/csv; charset=utf-8-sig');response.write('\ufeff');df[COLUMNS].to_csv(response,index=False,sep=';')
    elif kind=='xlsx':
        output=io.BytesIO();df[COLUMNS].to_excel(output,index=False,engine='openpyxl');response=HttpResponse(output.getvalue(),content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    elif kind=='pdf':
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        output=io.BytesIO();pdf=canvas.Canvas(output,pagesize=A4);y=800
        lines=['DATATRAN | Relatório do recorte','Fonte: CSV DATATRAN fornecido pelo usuário.', 'Filtros: '+json.dumps(parameters(request),ensure_ascii=False),*['%s: %s'%(k['label'],k['value']) for k in indicators(df)],*insights(df),'Metodologia: IDs únicos válidos; duplicidades mantêm a primeira linha.','Óbitos e feridos: soma de campos, preservando valores desconhecidos.','Coordenadas: envelope do Brasil, sem validação por fronteira.','Contagens absolutas não representam risco por exposição ao tráfego.','Causas registradas não demonstram causalidade estatística.']
        import textwrap
        pdf.setTitle('DATATRAN — Relatório analítico')
        for line in lines:
            for part in textwrap.wrap(line,95):
                if y<55:pdf.showPage();y=800
                pdf.setFont('Helvetica',10);pdf.drawString(42,y,part);y-=17
            y-=6
        pdf.save();response=HttpResponse(output.getvalue(),content_type='application/pdf')
    else:raise Http404()
    response['Content-Disposition']=f'attachment; filename="datatran-filtrado.{kind}"'
    return response
