/* Interface local: conteúdo dinâmico inserido com JSON seguro e APIs de texto. */
const body = document.body;
const storedTheme = (() => { try { return localStorage.getItem('datatran-theme'); } catch (_) { return null; } })();
if (storedTheme === 'dark') body.classList.add('dark');
const sidebarToggle = document.getElementById('sidebar-toggle');
const backdrop = document.getElementById('sidebar-backdrop');
function syncSidebar() {
    const mobile = window.matchMedia('(max-width:760px)').matches;
    const opened = mobile ? body.classList.contains('collapsed') : !body.classList.contains('collapsed');
    const visible = opened && !body.classList.contains('focus-layout');
    sidebarToggle.setAttribute('aria-expanded', String(visible));
    document.getElementById('sidebar').inert = !visible;
    backdrop.hidden = !(mobile && opened && !body.classList.contains('focus-layout'));
}
sidebarToggle.addEventListener('click', () => {body.classList.toggle('collapsed'); syncSidebar(); resizePlots();});
backdrop.addEventListener('click', () => {body.classList.remove('collapsed'); syncSidebar();});
const figures = JSON.parse(document.getElementById('chart-data')?.textContent || '[]');
const initialized = new WeakMap();
function plotTheme() {
    const dark = body.classList.contains('dark');
    return {font: {color: dark ? '#b6c7dd' : '#53657b'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)'};
}
function resizePlots() {
    requestAnimationFrame(() => document.querySelectorAll('.js-plotly-plot').forEach(plot => window.Plotly?.Plots.resize(plot)));
    setTimeout(() => document.querySelectorAll('.js-plotly-plot').forEach(plot => window.Plotly?.Plots.resize(plot)), 250);
}
function renderPlot(element) {
    if (initialized.has(element)) return initialized.get(element);
    const index = Number(element.id.split('-')[1]);
    const figure = figures[index]?.figure;
    if (!window.Plotly || !figure) {
        element.textContent = 'Não foi possível carregar este gráfico. Atualize a página.';
        return Promise.resolve();
    }
    const data = figure.data.map(trace => figure.data.length === 1 && trace.type === 'scatter' && (trace.stackgroup || trace.fill === 'tozeroy' || trace.fill === 'tonexty')
        ? {...trace, fillcolor:body.classList.contains('dark') ? 'rgba(134,164,201,.16)' : 'rgba(52,75,101,.12)'} : trace);
    const promise = Plotly.newPlot(element, data, {...figure.layout, ...plotTheme(),
        font:{...figure.layout.font, ...plotTheme().font}}, {
        responsive:true, displaylogo:false, displayModeBar:'hover', locale:'pt-BR',
        toImageButtonOptions:{format:'png', filename:'datatran-grafico', scale:2}
    });
    initialized.set(element, promise);
    return promise;
}
if (window.IntersectionObserver) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
        if (entry.isIntersecting) {renderPlot(entry.target); observer.unobserve(entry.target);}
    }), {rootMargin:'200px'});
    document.querySelectorAll('.plot').forEach(plot => observer.observe(plot));
} else document.querySelectorAll('.plot').forEach(renderPlot);
document.getElementById('theme-toggle').addEventListener('click', () => {
    body.classList.toggle('dark');
    try {localStorage.setItem('datatran-theme', body.classList.contains('dark') ? 'dark' : 'light');} catch (_) {}
    document.querySelectorAll('.js-plotly-plot').forEach(plot => Plotly.relayout(plot, plotTheme()));
});
const focusToggle = document.getElementById('focus-toggle');
focusToggle.addEventListener('click', () => {
    const enabled = body.classList.toggle('focus-layout');
    focusToggle.setAttribute('aria-pressed', String(enabled));
    focusToggle.querySelector('span').textContent = enabled ? 'Sair da apresentação' : 'Apresentar';
    syncSidebar(); resizePlots();
});
let expandedCard = null;
function closeExpanded() {
    if (!expandedCard) return;
    const card = expandedCard, plot = card.querySelector('.plot'), button = card.querySelector('.chart-expand');
    card.classList.remove('chart-maximized'); body.classList.remove('chart-open');
    button.setAttribute('aria-pressed', 'false'); button.setAttribute('aria-label', 'Ampliar gráfico: ' + card.querySelector('h2').textContent);
    button.title = 'Ampliar gráfico';
    Plotly.relayout(plot, {height: Number(card.dataset.plotHeight || 290), width:plot.clientWidth, autosize:true});
    expandedCard = null; button.focus(); resizePlots();
}
document.querySelectorAll('.chart-expand').forEach(button => button.addEventListener('click', async () => {
    const card = button.closest('.chart-card'), plot = card.querySelector('.plot');
    if (expandedCard === card) {closeExpanded(); return;}
    closeExpanded(); await renderPlot(plot);
    if (!plot.layout) return;
    card.dataset.plotHeight = plot.layout.height;
    card.classList.add('chart-maximized'); body.classList.add('chart-open'); expandedCard = card;
    button.setAttribute('aria-pressed','true'); button.setAttribute('aria-label','Reduzir gráfico: ' + card.querySelector('h2').textContent); button.title = 'Reduzir gráfico';
    Plotly.relayout(plot, {height: Math.max(240, window.innerHeight - card.querySelector('.chart-heading').offsetHeight - 90), width:plot.clientWidth, autosize:true});
    resizePlots();
}));
document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (expandedCard) closeExpanded();
    else if (body.classList.contains('focus-layout')) focusToggle.click();
    else if (window.matchMedia('(max-width:760px)').matches) {body.classList.remove('collapsed'); syncSidebar();}
});
window.addEventListener('resize', () => {
    syncSidebar();
    if (expandedCard) Plotly.relayout(expandedCard.querySelector('.plot'), {height:Math.max(240,window.innerHeight - expandedCard.querySelector('.chart-heading').offsetHeight - 90)});
});
syncSidebar();
document.querySelectorAll('form').forEach(form => form.addEventListener('submit', () => {document.getElementById('loading').hidden = false;}));
window.addEventListener('pageshow', () => {document.getElementById('loading').hidden = true;});
const uf = document.querySelector('select[name="uf"]');
uf?.addEventListener('change', () => {document.querySelector('select[name="municipio"]').value = ''; document.getElementById('filters').requestSubmit();});

if(window.L)L.Icon.Default.imagePath='';
if(window.L)L.Icon.Default.mergeOptions({iconUrl:'/static/dashboard/vendor/marker-icon.png',iconRetinaUrl:'/static/dashboard/vendor/marker-icon.png',shadowUrl:'/static/dashboard/vendor/marker-shadow.png'});
const mapJSON=document.getElementById('map-data');
if(mapJSON){const data=JSON.parse(mapJSON.textContent),map=L.map('map').setView([-14,-51],4);/* Fundos do mapa: satélite (Esri) com divisas e nomes por cima; alternativa em mapa de ruas (CARTO). */const rp={referrerPolicy:'strict-origin-when-cross-origin'};const satellite=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{...rp,maxZoom:19,attribution:'Imagens © Esri, Maxar, Earthstar Geographics'});const borders=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',{...rp,maxZoom:19,attribution:'Divisas © Esri'});const streets=L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',{...rp,subdomains:'abcd',maxZoom:19,attribution:'© OpenStreetMap contributors © CARTO'});satellite.addTo(map);borders.addTo(map);const clusters=L.markerClusterGroup({chunkedLoading:true}),heat=[];data.points.forEach(p=>{const box=document.createElement('div');box.textContent=`${p.municipio} / ${p.uf} · BR ${p.br??'—'} · Óbitos: ${p.mortos??'não informado'}`;clusters.addLayer(L.marker([p.latitude,p.longitude]).bindPopup(box));heat.push([p.latitude,p.longitude,1])});clusters.addTo(map);const density=L.heatLayer(heat,{radius:20,blur:18,maxZoom:12});L.control.layers({'Satélite':satellite,'Mapa de ruas':streets},{'Divisas e nomes':borders,'Pontos agrupados':clusters,'Densidade dos pontos exibidos':density},{collapsed:false}).addTo(map);if(data.points.length)map.fitBounds(clusters.getBounds(),{padding:[20,20],maxZoom:11})}
