"""Exporta um snapshot de apresentação em um único HTML, sem depender do Django."""
import base64
import json
from pathlib import Path
import re

import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpRequest, QueryDict
from django.utils import timezone

from dashboard.views import NAV, index
from dashboard.services.data_loader import load
from dashboard.services.data_cleaning import COUNTS
from dashboard.services.filters import FIELDS


def safe_json(value):
    return json.dumps(value,ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')


def data_uri(path):
    mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg'
    return f'data:{mime};base64,'+base64.b64encode(path.read_bytes()).decode()


def browser_data(df):
    """Colunas compactas: codes de catégories et valeurs nulles préservées."""
    categories={}
    for field in FIELDS:
        series=df[field].astype('string')
        if field=='br':series=series.str.replace(r'\.0$','',regex=True)
        codes,values=pd.factorize(series,sort=True)
        categories[field]={'values':values.tolist(),'codes':codes.tolist()}
    return {'count':len(df),'categories':categories,'dates':df.data_inversa.dt.strftime('%Y-%m-%d').tolist(),
            'ids':df.id.astype('string').tolist(),'hours':json.loads(df.hora.to_json(orient='values')),
            'metrics':{field:json.loads(df[field].to_json(orient='values')) for field in COUNTS},
            'labels':{**FIELDS,'inicio':'Data inicial','fim':'Data final','hora_inicio':'Hora inicial','hora_fim':'Hora final','q':'Pesquisa'}}


class Command(BaseCommand):
    help='Gera dashboard.html com as nove abas e dados incorporados (filtros locais na Visão Geral).'

    def add_arguments(self,parser):
        parser.add_argument('--output',default='dashboard.html',help='Arquivo HTML de saída.')

    def handle(self,*args,**options):
        static=settings.BASE_DIR/'dashboard/static/dashboard'
        figures=[];sections=[];maps={};titles={};base=None;overview_indices=[]
        raw,_=load()
        local_data=browser_data(raw)
        exported=timezone.localdate().strftime('%d/%m/%Y')
        for slug,title,_ in NAV:
            request=HttpRequest();request.method='GET'
            request.GET=QueryDict('visual=simples');request.session={}
            request.META.update(SERVER_NAME='localhost',SERVER_PORT='8000')
            response=index(request,page=slug)
            if response.status_code!=200:raise CommandError(f'Falha ao renderizar {title}.')
            html=response.content.decode()
            if 'id="chart-data"' not in html:raise CommandError(f'Dados indisponíveis para {title}.')
            if base is None:base=html
            titles[slug]=title
            body=html.split('<div class="workspace">',1)[1].rsplit('</div></main>',1)[0]
            match=re.search(r'<script id="chart-data"[^>]*>(.*?)</script>',body,re.S)
            charts=json.loads(match.group(1))
            offset=len(figures)
            if slug=='overview':
                kinds={'Sinistros ao longo dos meses':'monthly','5 estados com mais sinistros':'states',
                       'Como os sinistros são classificados?':'classification','5 causas mais registradas':'causes'}
                for position,chart in enumerate(charts):
                    if chart['title'] not in kinds:raise CommandError('Gráfico da Visão Geral sem regra de filtro local: '+chart['title'])
                    overview_indices.append({'index':offset+position,'kind':kinds[chart['title']]})
            figures.extend(charts)
            body=re.sub(r'id="chart-(\d+)"',lambda m:f'id="chart-{int(m.group(1))+offset}"',body)
            match=re.search(r'<script id="map-data"[^>]*>(.*?)</script>',body,re.S)
            if match:
                maps[slug]=json.loads(match.group(1))
                body=body.replace('id="map"',f'id="map-{slug}" class="export-map"')
                body=body.replace('KPIs usam a base completa.','Indicadores e gráficos usam todo o recorte.')
            body=re.sub(r'<script\b[^>]*>.*?</script>','',body,flags=re.S)
            overview_form=''
            if slug=='overview':
                overview_form=re.search(r'<form\b[^>]*id="filters"[^>]*>.*?</form>',body,re.S).group(0)
                overview_form=overview_form.replace('<a href="?limpar=1">','<a href="#overview" id="overview-clear">')
                overview_form=overview_form.replace('<input type="hidden" name="aplicar" value="1">','')
                overview_form+='\n<div id="overview-empty" class="notice" role="status" hidden>Nenhum registro encontrado. Ajuste ou limpe os filtros.</div>'
            body=re.sub(r'<form\b[^>]*>.*?</form>','',body,flags=re.S)
            body=re.sub(r'<div class="quick">.*?</div>','',body,flags=re.S)
            body=re.sub(r'<div class="pagination">.*?</div>','',body,flags=re.S)
            body=re.sub(r'<a\b[^>]*href="/exportar/(?:csv|xlsx)/[^\"]*"[^>]*>.*?</a>','',body,flags=re.S)
            body=re.sub(r'<a\b[^>]*href="\?visual=[^\"]*"[^>]*>.*?</a>','',body,flags=re.S)
            body=re.sub(r'<a class="button report-button"[^>]*>.*?</a>', '<button type="button" class="button report-button" onclick="window.print()">Imprimir página</button>',body,flags=re.S)
            body=body.replace('30 registros por página · exportação inclui todo o recorte','Prévia de até 30 registros. A consulta completa está disponível na aplicação Django.')
            body=body.replace('id="page-title"',f'id="title-{slug}"').replace('aria-labelledby="page-title"',f'aria-labelledby="title-{slug}"')
            snapshot=f'<div class="snapshot-note">Arquivo de apresentação · gerado em {exported}. Filtros locais disponíveis na Visão Geral. As demais abas mostram a base completa; Paraíba em foco usa somente PB.</div>'
            heading_end=body.index('</section>')+len('</section>')
            body=body[:heading_end]+snapshot+overview_form+body[heading_end:]
            hidden='' if slug=='overview' else ' hidden'
            sections.append(f'<section class="export-page" id="page-{slug}" data-page="{slug}"{hidden}>{body}</section>')
            self.stdout.write(f'Incluída: {title} ({len(charts)} gráficos)')
        prefix=base.split('<div class="workspace">',1)[0]
        prefix=re.sub(r'<link\b[^>]*>','',prefix)
        prefix=re.sub(r'<script\b[^>]*>.*?</script>','',prefix,flags=re.S)
        prefix=prefix.replace('href="/"','href="#overview"')
        for slug,_,_ in NAV:
            prefix=prefix.replace(f'href="/{slug}/"',f'href="#{slug}"')
        prefix=prefix.replace('/static/dashboard/images/brasao-pmpb.png',data_uri(static/'images/brasao-pmpb.png'))
        # O brasão da PRF já usado pela aplicação é opcional quando não há cópia local.
        prf=static/'images/brasao-prf.png'
        if prf.exists():prefix=prefix.replace('https://upload.wikimedia.org/wikipedia/commons/1/1b/PRF_new.png',data_uri(prf))
        else:
            prefix=re.sub(r'<img src="https://upload.wikimedia.org/[^\"]+"[^>]*>','',prefix)
        css_files=['vendor/bootstrap.min.css','vendor/leaflet.css','vendor/MarkerCluster.css','vendor/MarkerCluster.Default.css','panel.css']
        styles='\n'.join((static/name).read_text() for name in css_files)
        styles+='''
.export-page[hidden]{display:none!important}.export-map{height:480px;border-radius:10px;z-index:1;margin-top:16px}.snapshot-note{padding:13px 17px;margin:0 0 22px;border:1px solid var(--border);background:var(--surface);border-radius:9px;color:var(--muted);font-size:.8rem}
@media print{.sidebar,header,.visual-toolbar,.chart-expand,.snapshot-note,.skip-link{display:none!important}main{margin:0!important}.workspace{padding:0;max-width:none}.heading{background:#fff!important;color:#172b45;box-shadow:none}.heading p,.heading .eyebrow{color:#53657b}.heading-side .report-button{display:none}.charts{display:block}.chart-card{break-inside:avoid;margin-bottom:20px!important}.export-map{height:400px}.card,.kpi{box-shadow:none}body{background:#fff}footer{break-inside:avoid}}
'''
        prefix=prefix.replace('</head>','<style>'+styles+'</style></head>')
        output=prefix+'<div class="workspace">'+''.join(sections)+'</div></main><div id="loading" role="status" hidden>Carregando…</div>'
        output+='<script id="chart-data" type="application/json">'+safe_json(figures)+'</script>'
        output+='<script id="export-maps" type="application/json">'+safe_json(maps)+'</script>'
        output+='<script id="export-titles" type="application/json">'+safe_json(titles)+'</script>'
        output+='<script id="overview-local-data" type="application/json">'+safe_json(local_data)+'</script>'
        output+='<script id="overview-chart-schema" type="application/json">'+safe_json(overview_indices)+'</script>'
        libraries=['vendor/plotly.min.js','vendor/plotly-locale-pt-br.js','vendor/leaflet.js','vendor/leaflet.markercluster.js','vendor/leaflet-heat.js']
        for name in libraries:
            output+='<script>'+(static/name).read_text().replace('</script','<\\/script')+'</script>'
        ui=(static/'panel.js').read_text().split("if(window.L)L.Icon.Default.imagePath",1)[0]
        ui=ui.split("const uf = document.querySelector",1)[0]
        output+='<script>'+ui+'</script>'
        export_js=(Path(__file__).with_name('exportar_html_ui.js')).read_text()
        export_js=export_js.replace('"__MARKER_ICON__"',json.dumps(data_uri(static/'vendor/marker-icon.png'))).replace('"__MARKER_SHADOW__"',json.dumps(data_uri(static/'vendor/marker-shadow.png')))
        output+='<script>'+export_js+'</script>'
        filter_js=Path(__file__).with_name('exportar_html_filters.js').read_text()
        output+='<script>'+filter_js+'</script></body></html>'
        target=Path(options['output']).resolve();target.parent.mkdir(parents=True,exist_ok=True);target.write_text(output,encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'HTML criado: {target} ({target.stat().st_size/1024**2:.2f} MB, {len(figures)} gráficos).'))
