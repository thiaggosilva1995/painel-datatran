/* Filtros da Visão Geral executados sobre a base tratada incorporada ao HTML. */
const localSource = JSON.parse(document.getElementById('overview-local-data').textContent);
const overviewSchema = JSON.parse(document.getElementById('overview-chart-schema').textContent);
const overviewForm = document.querySelector('#page-overview #filters');
const overviewPage = document.getElementById('page-overview');
const overviewTemplates = new Map(overviewSchema.map(spec => [spec.index,JSON.parse(JSON.stringify(figures[spec.index].figure))]));
const categoryLookups = new Map(Object.entries(localSource.categories).map(([field,data]) => [field,new Map(data.values.map((value,index)=>[value,index]))]));
const localMonths = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
let overviewRevision = 0;
function categoryValue(field,row) {
    const column=localSource.categories[field],code=column.codes[row];
    return code<0?'Não informado':column.values[code];
}
function localNumber(value,decimals=0) {
    if(value===null || !Number.isFinite(value)) return 'Não informado';
    // Mantém o arredondamento de empate para o par usado no backend Python.
    const scale=10**decimals,scaled=value*scale,lower=Math.floor(scaled);
    const rounded=Math.abs(scaled-lower-.5)<1e-10 ? (lower%2===0?lower:lower+1) : Math.round(scaled);
    return (rounded/scale).toLocaleString('pt-BR',{minimumFractionDigits:decimals,maximumFractionDigits:decimals});
}
function overviewRows(params) {
    const conditions=Object.keys(localSource.categories).filter(field=>params[field]).map(field=>({codes:localSource.categories[field].codes,code:categoryLookups.get(field).get(params[field])??-2}));
    const query=(params.q||'').slice(0,100).toLocaleLowerCase('pt-BR');
    const rows=[];
    for(let i=0;i<localSource.count;i++) {
        if(conditions.some(condition=>condition.codes[i]!==condition.code)) continue;
        const date=localSource.dates[i],hour=localSource.hours[i];
        if(params.inicio && date<params.inicio || params.fim && date>params.fim) continue;
        if(params.hora_inicio && (hour===null || hour<Number(params.hora_inicio))) continue;
        if(params.hora_fim && (hour===null || hour>Number(params.hora_fim))) continue;
        if(query && !categoryValue('municipio',i).toLocaleLowerCase('pt-BR').includes(query) && !localSource.ids[i].includes(query) && !categoryValue('br',i).includes(query)) continue;
        rows.push(i);
    }
    return rows;
}
function localSum(rows,field) {
    let sum=0,known=0;
    for(const row of rows) {const value=localSource.metrics[field][row];if(value!==null){sum+=value;known++;}}
    return known?sum:null;
}
function countGroups(rows,field) {
    const result=new Map();
    for(const row of rows){const value=field==='date'?localSource.dates[row].slice(0,7):categoryValue(field,row);result.set(value,(result.get(value)||0)+1);}
    return [...result].sort((a,b)=>b[1]-a[1]);
}
function refreshDependentOptions() {
    const uf=overviewForm.elements.namedItem('uf').value;
    const ufCode=categoryLookups.get('uf').get(uf);
    for(const field of ['municipio','br','delegacia','uop']) {
        const select=overviewForm.elements.namedItem(field),previous=select.value;
        const column=localSource.categories[field],available=new Set();
        for(let row=0;row<localSource.count;row++) {
            if(uf && localSource.categories.uf.codes[row]!==ufCode) continue;
            if(column.codes[row]>=0)available.add(column.codes[row]);
        }
        const fragment=document.createDocumentFragment();fragment.append(new Option('Todos',''));
        for(const code of [...available].sort((a,b)=>a-b)) fragment.append(new Option(column.values[code],column.values[code]));
        select.replaceChildren(fragment);
        if([...select.options].some(option=>option.value===previous))select.value=previous;
    }
}
function overviewDateLabel(date) {return date.split('-').reverse().join('/');}
function updateOverviewCards(rows,params) {
    const deaths=localSum(rows,'mortos'),total=rows.length;
    const topUF=countGroups(rows,'uf').find(([uf])=>uf!=='Não informado');
    const fatal=rows.filter(row=>(localSource.metrics.mortos[row]??0)>0).length;
    const values={
        'Sinistros registrados':localNumber(total),'Óbitos':localNumber(deaths),
        'Feridos':localNumber(localSum(rows,'feridos')),'Feridos graves':localNumber(localSum(rows,'feridos_graves')),
        'Feridos leves':localNumber(localSum(rows,'feridos_leves')),'Veículos envolvidos':localNumber(localSum(rows,'veiculos')),
        'Pessoas envolvidas':localNumber(localSum(rows,'pessoas')),'Sinistros com óbitos':localNumber(fatal),
        'Óbitos / 100 sinistros':localNumber(total && deaths!==null?100*deaths/total:null),
        'Sinistros fatais (%)':localNumber(total?100*fatal/total:null,1),'UF com mais sinistros':topUF?topUF[0]:'Sem dados'
    };
    overviewPage.querySelectorAll('.kpi').forEach(card=>{const label=card.querySelector('.kpi-top>span').textContent.trim();card.querySelector(':scope>strong').textContent=values[label]??'Não informado';});
    let first=null,last=null;
    for(const row of rows){const date=localSource.dates[row];if(first===null||date<first)first=date;if(last===null||date>last)last=date;}
    overviewPage.querySelector('.section-caption>span:last-child').textContent=localNumber(total)+' registros · '+(total?overviewDateLabel(first)+' — '+overviewDateLabel(last):'Sem dados');
    document.getElementById('overview-empty').textContent='Nenhum registro encontrado. Ajuste ou limpe os filtros.';
    document.getElementById('overview-empty').hidden=total>0;
    overviewForm.dataset.filteredCount=String(total);
    let active=overviewForm.querySelector('.active-filters');
    if(!active){active=document.createElement('div');active.className='active-filters';active.setAttribute('aria-label','Filtros aplicados');overviewForm.querySelector('details').before(active);}
    active.replaceChildren();
    for(const [key,value] of Object.entries(params))if(value && localSource.labels[key]){
        const badge=document.createElement('span'),label=document.createElement('strong');label.textContent=localSource.labels[key]+': ';badge.append(label,document.createTextNode(value));active.append(badge);
    }
    active.hidden=!active.childElementCount;
}
function filteredOverviewFigure(spec,rows) {
    const figure=JSON.parse(JSON.stringify(overviewTemplates.get(spec.index)));
    delete figure.layout.annotations;
    if(!rows.length) {
        figure.data=[];figure.layout.showlegend=false;
        figure.layout.xaxis={...figure.layout.xaxis,visible:false};figure.layout.yaxis={...figure.layout.yaxis,visible:false};
        figure.layout.annotations=[{text:'Nenhum registro neste recorte',xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false,font:{size:15}}];
        return figure;
    }
    const trace=figure.data[0];
    if(spec.kind==='monthly') {
        const groups=countGroups(rows,'date').sort((a,b)=>a[0].localeCompare(b[0]));
        trace.x=groups.map(([date])=>date);trace.y=groups.map(([,value])=>value);
        figure.layout.xaxis.tickvals=trace.x;
        figure.layout.xaxis.ticktext=trace.x.map(date=>localMonths[Number(date.slice(5,7))-1]+'/'+date.slice(2,4));
    } else if(spec.kind==='states') {
        const groups=countGroups(rows,'uf').slice(0,5);
        trace.x=groups.map(([label])=>label);trace.y=groups.map(([,value])=>value);trace.customdata=groups.map(([label])=>[label]);
    } else if(spec.kind==='causes') {
        const groups=countGroups(rows,'causa_acidente').slice(0,5).reverse();
        trace.y=groups.map(([label])=>label);trace.x=groups.map(([,value])=>value);
        figure.layout.yaxis.tickvals=trace.y;figure.layout.yaxis.ticktext=trace.y.map(value=>value.length<=36?value:value.slice(0,33)+'…');
    } else if(spec.kind==='classification') {
        const groups=countGroups(rows,'classificacao_acidente'),selected=groups.slice(0,4);
        if(groups.length>4)selected.push(['Demais categorias',groups.slice(4).reduce((sum,[,value])=>sum+value,0)]);
        trace.labels=selected.map(([label])=>label.length<=32?label:label.slice(0,29)+'…');trace.values=selected.map(([,value])=>value);trace.customdata=selected.map(([label])=>label);
    }
    return figure;
}
async function applyOverviewFilters() {
    const revision=++overviewRevision;
    const params=Object.fromEntries(new FormData(overviewForm));
    document.getElementById('loading').hidden=false;
    try {
        await new Promise(resolve=>requestAnimationFrame(resolve));
        if(revision!==overviewRevision)return;
        if(expandedCard)closeExpanded();
        const rows=overviewRows(params);updateOverviewCards(rows,params);
        for(const spec of overviewSchema) {
            const plot=document.getElementById('chart-'+spec.index),figure=filteredOverviewFigure(spec,rows);
            figures[spec.index].figure=figure;
            await renderPlot(plot);
            if(revision!==overviewRevision)return;
            const data=figure.data.map(trace=>figure.data.length===1&&trace.type==='scatter'&&trace.stackgroup?{...trace,fillcolor:body.classList.contains('dark')?'rgba(134,164,201,.16)':'rgba(52,75,101,.12)'}:trace);
            await Plotly.react(plot,data,{...figure.layout,...plotTheme(),font:{...figure.layout.font,...plotTheme().font}},
                {responsive:true,displaylogo:false,displayModeBar:'hover',locale:'pt-BR',toImageButtonOptions:{format:'png',filename:'datatran-grafico',scale:2}});
        }
    } finally {if(revision===overviewRevision)document.getElementById('loading').hidden=true;}
}
overviewForm.addEventListener('submit',event=>{event.preventDefault();applyOverviewFilters().catch(error=>{console.error(error);const status=document.getElementById('overview-empty');status.textContent='Não foi possível atualizar o recorte. Limpe os filtros e tente novamente.';status.hidden=false;});});
overviewForm.elements.namedItem('uf').addEventListener('change',()=>{
    overviewForm.elements.namedItem('municipio').value='';refreshDependentOptions();overviewForm.requestSubmit();
});
document.getElementById('overview-clear').addEventListener('click',event=>{
    event.preventDefault();overviewForm.reset();refreshDependentOptions();applyOverviewFilters();
});
refreshDependentOptions();overviewForm.dataset.filteredCount=String(localSource.count);
