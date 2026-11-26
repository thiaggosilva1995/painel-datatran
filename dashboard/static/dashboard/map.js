/* OpenStreetMap como fundo padrão; camada local disponível como alternativa. */
(() => {
    const element = document.getElementById('map');
    const source = document.getElementById('map-data');
    if (!element || !source) return;
    const status = document.getElementById('map-status');
    if (!window.L) {
        status.textContent = 'Não foi possível carregar a biblioteca local do mapa. Atualize a página.';
        return;
    }
    try {
        const data = JSON.parse(source.textContent);
        const map = L.map(element, {
            dragging: true, scrollWheelZoom: true, doubleClickZoom: true,
            touchZoom: true, keyboard: true, zoomControl: true, minZoom: 3, maxZoom: 18
        }).setView(element.dataset.state ? [-7.1, -36.7] : [-14, -51], element.dataset.state ? 7 : 4);
        map.createPane('boundaries');
        map.getPane('boundaries').style.zIndex = '250';
        const local = L.layerGroup();
        const streets = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors', maxZoom: 18
        });
        let failedTiles = false;
        streets.on('tileerror', () => {
            if (!map.hasLayer(streets)) return;
            failedTiles = true;
            status.textContent = 'Alguns detalhes do mapa online não carregaram. Verifique a conexão ou selecione “Mapa local (IBGE)” no controle de camadas.';
        });
        streets.on('load', () => {
            if (!failedTiles) status.textContent = 'Arraste para navegar; use +/− ou a roda do mouse para ampliar.';
        });
        // Fundo original com nomes de cidades e ruas; a alternativa local é opcional.
        streets.addTo(map);
        const points = typeof L.markerClusterGroup === 'function'
            ? L.markerClusterGroup({chunkedLoading: true, chunkInterval: 100, chunkDelay: 25})
            : L.layerGroup();
        const heatPoints = [], markers = [], positions = [];
        for (const point of data.points) {
            if (!Number.isFinite(point.latitude) || !Number.isFinite(point.longitude)) continue;
            const position = [point.latitude, point.longitude];
            const popup = document.createElement('div');
            popup.textContent = `${point.municipio ?? 'Não informado'} / ${point.uf ?? '—'} · BR ${point.br ?? '—'} · Óbitos: ${point.mortos ?? 'não informado'}`;
            markers.push(L.circleMarker(position, {
                radius: 6, color: '#fff', weight: 1, fillColor: point.mortos > 0 ? '#b33745' : '#2376df', fillOpacity: .85
            }).bindPopup(popup));
            positions.push(position);
            heatPoints.push([...position, 1]);
        }
        points.addTo(map);
        if (points.addLayers) points.addLayers(markers);
        else markers.forEach(marker => points.addLayer(marker));
        const overlays = {'Pontos de sinistros': points};
        if (typeof L.heatLayer === 'function') overlays['Densidade dos pontos exibidos'] = L.heatLayer(heatPoints, {radius: 20, blur: 18, maxZoom: 12});
        L.control.layers({'Mapa local (IBGE)': local, 'Ruas (online)': streets}, overlays).addTo(map);
        const fit = () => {
            map.invalidateSize();
            if (positions.length) map.fitBounds(L.latLngBounds(positions), {padding: [25, 25], maxZoom: 11});
        };
        fit();
        document.getElementById('map-reset').addEventListener('click', fit);
        const expand = document.getElementById('map-expand');
        const card = element.closest('.map-card');
        expand.addEventListener('click', () => {
            const expanded = card.classList.toggle('map-expanded');
            expand.setAttribute('aria-pressed', String(expanded));
            expand.textContent = expanded ? 'Reduzir mapa' : 'Ampliar mapa';
            document.body.classList.toggle('map-open', expanded);
            requestAnimationFrame(() => map.invalidateSize());
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && card.classList.contains('map-expanded')) expand.click();
        });
        if (window.ResizeObserver) new ResizeObserver(() => map.invalidateSize()).observe(element);
        window.addEventListener('resize', () => map.invalidateSize());
        status.textContent = positions.length
            ? 'Arraste para navegar; use +/− ou a roda do mouse para ampliar.'
            : 'Nenhum ponto com coordenadas válidas neste recorte. A referência territorial permanece disponível.';
        fetch(element.dataset.boundaries)
            .then(response => {if (!response.ok) throw new Error('malha indisponível'); return response.json();})
            .then(geo => {
                const state = element.dataset.state;
                L.geoJSON(geo, {
                    pane: 'boundaries', interactive: false, attribution: 'Limites simplificados: IBGE',
                    filter: feature => !state || String(feature.properties.codarea) === state,
                    style: {color: '#758ba3', weight: 1.2, fillColor: '#dce7ef', fillOpacity: .55},
                    onEachFeature: (feature, layer) => {
                        if (feature.properties.nome) layer.bindTooltip(String(feature.properties.nome));
                    }
                }).addTo(local);
            })
            .catch(() => {
                if (map.hasLayer(local)) status.textContent = 'Limites locais indisponíveis. Selecione “Ruas (online)” para voltar ao mapa original.';
            });
    } catch (error) {
        status.textContent = 'Não foi possível iniciar o mapa. Atualize a página e tente novamente.';
        console.error('Falha na inicialização do mapa:', error);
    }
})();
