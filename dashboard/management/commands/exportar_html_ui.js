/* Navegação do snapshot: somente recursos incorporados; fundos cartográficos online. */
const exportTitles = JSON.parse(document.getElementById('export-titles').textContent);
const exportMaps = JSON.parse(document.getElementById('export-maps').textContent);
const activeMaps = new Map();
L.Icon.Default.imagePath='';
L.Icon.Default.mergeOptions({iconUrl:"__MARKER_ICON__",iconRetinaUrl:"__MARKER_ICON__",shadowUrl:"__MARKER_SHADOW__"});
function initializeExportMap(slug) {
    if (!exportMaps[slug]) return;
    if (activeMaps.has(slug)) {activeMaps.get(slug).invalidateSize();return;}
    const data=exportMaps[slug],map=L.map('map-'+slug).setView(slug==='paraiba'?[-7.1,-36.7]:[-14,-51],slug==='paraiba'?7:4);
    const rp={referrerPolicy:'strict-origin-when-cross-origin'};
    const satellite=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{...rp,maxZoom:19,attribution:'Imagens © Esri, Maxar, Earthstar Geographics'});
    const borders=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',{...rp,maxZoom:19,attribution:'Divisas © Esri'});
    const streets=L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',{...rp,subdomains:'abcd',maxZoom:19,attribution:'© OpenStreetMap contributors © CARTO'});
    satellite.addTo(map);borders.addTo(map);
    const clusters=L.markerClusterGroup({chunkedLoading:true}),heat=[];
    const markers=data.points.map(p=>{const popup=document.createElement('div');popup.textContent=`${p.municipio} / ${p.uf} · BR ${p.br??'—'} · Óbitos: ${p.mortos??'não informado'}`;heat.push([p.latitude,p.longitude,1]);return L.marker([p.latitude,p.longitude]).bindPopup(popup);});
    clusters.addTo(map);clusters.addLayers(markers);
    const density=L.heatLayer(heat,{radius:20,blur:18,maxZoom:12});
    L.control.layers({'Satélite':satellite,'Mapa de ruas':streets},{'Divisas e nomes':borders,'Pontos agrupados':clusters,'Densidade dos pontos exibidos':density},{collapsed:false}).addTo(map);
    if(data.points.length)map.fitBounds(L.latLngBounds(data.points.map(p=>[p.latitude,p.longitude])),{padding:[20,20],maxZoom:11});
    activeMaps.set(slug,map);
}
function showExportPage() {
    const requested=location.hash.slice(1),slug=Object.hasOwn(exportTitles,requested)?requested:'overview';
    if(expandedCard)closeExpanded();
    document.querySelectorAll('.export-page').forEach(section=>{section.hidden=section.dataset.page!==slug;});
    Object.keys(exportTitles).forEach(page=>body.classList.remove('page-'+page));
    body.classList.add('page-'+slug);
    document.querySelector('.breadcrumb strong').textContent=exportTitles[slug];
    document.title=exportTitles[slug]+' · DATATRAN';
    document.querySelectorAll('nav a').forEach(link=>{const active=link.hash==='#'+slug;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
    if(window.matchMedia('(max-width:760px)').matches)body.classList.remove('collapsed');
    syncSidebar();window.scrollTo(0,0);resizePlots();initializeExportMap(slug);
}
window.addEventListener('hashchange',showExportPage);
window.addEventListener('resize',()=>activeMaps.forEach(map=>map.invalidateSize()));
showExportPage();
