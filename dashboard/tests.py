import io
import tempfile
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch
import pandas as pd
from django.conf import settings
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .services.data_loader import load, read_file
from .services.data_cleaning import clean, COLUMNS
from .services.filters import apply
from .services.indicators import indicators
from .models import Importacao


class DataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.df,cls.report=load()

    def test_original_validation(self):
        self.assertEqual(self.report['recebidos'],54895)
        self.assertEqual(len(self.df.loc[self.df.uf.eq('PB')]),1358)
        self.assertEqual(self.df.data_inversa.min().strftime('%Y-%m-%d'),'2026-01-01')
        self.assertEqual(self.df.data_inversa.max().strftime('%Y-%m-%d'),'2026-09-30')

    def test_latin1_dates_coordinates_and_unknown(self):
        raw=pd.read_csv(settings.BASE_DIR/'data/datatran2026.csv',encoding='latin1',sep=';',nrows=2)
        raw.loc[0,'mortos']=float('nan')
        raw.loc[0,'latitude']='-7,291548'
        raw.loc[1,'data_inversa']='inválida'
        encoded=raw.to_csv(sep=';',index=False).encode('latin1')
        df,report=clean(read_file(io.BytesIO(encoded),'teste.csv'))
        self.assertEqual(len(df),1)
        self.assertTrue(pd.isna(df.iloc[0].mortos))
        self.assertAlmostEqual(df.iloc[0].latitude,-7.291548)
        self.assertEqual(report['rejeitados'],1)

    def test_unique_and_sums(self):
        raw=self.df.head(2)[COLUMNS]
        df,report=clean(pd.concat([raw,raw.head(1)]))
        self.assertEqual(df.id.nunique(),2)
        self.assertEqual(report['duplicados'],1)
        self.assertEqual(df.mortos.sum(),raw.mortos.sum())
        self.assertEqual(df.feridos.sum(),raw.feridos.sum())

    def test_filters_preserve_original(self):
        original=self.df.copy(deep=True)
        selected=apply(self.df,{'uf':'PB','municipio':'JOAO PESSOA','inicio':'2026-02-01','fim':'2026-02-28'})
        self.assertTrue(selected.uf.eq('PB').all())
        self.assertTrue(selected.municipio.eq('JOAO PESSOA').all())
        self.assertTrue(selected.data_inversa.between('2026-02-01','2026-02-28').all())
        selected['mortos']=999
        pd.testing.assert_frame_equal(self.df,original)

    def test_all_routes(self):
        from .views import PAGES
        count=0
        for page,_,_ in PAGES:
            with self.subTest(page=page):
                r=self.client.get('/' if page=='overview' else f'/{page}/')
                self.assertEqual(r.status_code,200)
                count+=len(r.context.get('figures',[]))
                if page=='paraiba':self.assertEqual(r.context['rows'],1358)
        self.assertGreaterEqual(count,35)

    def test_empty(self):
        r=self.client.get('/',{'uf':'XX'})
        self.assertContains(r,'Nenhum registro encontrado')
        self.assertEqual(r.context['figures'],[])

    def test_exports(self):
        for kind in ['csv','xlsx','pdf']:
            r=self.client.get(f'/exportar/{kind}/',{'uf':'PB'})
            self.assertEqual(r.status_code,200)
            self.assertTrue(r.content)
        self.assertTrue(self.client.get('/exportar/pdf/').content.startswith(b'%PDF'))

    def test_upload_preview_and_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data/raw').mkdir(parents=True);(root/'data/processed').mkdir()
            self.df.head(4)[COLUMNS].to_csv(root/'data/datatran2026.csv',sep=';',index=False)
            with override_settings(BASE_DIR=root):
                before=(root/'data/datatran2026.csv').read_bytes()
                file=SimpleUploadedFile('nova.csv',self.df.head(2)[COLUMNS].to_csv(sep=';',index=False).encode())
                r=self.client.post('/upload/',{'arquivo':file})
                self.assertEqual(r.status_code,200)
                self.assertEqual(Importacao.objects.count(),1)
                self.assertFalse((root/'data/processed/active.csv').exists())
                r=self.client.post('/upload/',{'acao':'ativar'})
                self.assertEqual(r.status_code,302)
                self.assertTrue((root/'data/processed/active.csv').exists())
                self.assertEqual(len(load()[0]),2)
                self.assertEqual((root/'data/datatran2026.csv').read_bytes(),before)
                self.assertEqual(len(list((root/'data/raw').glob('backup-*'))),1)

    def test_upload_errors_and_zip(self):
        r=self.client.post('/upload/',{'arquivo':SimpleUploadedFile('bad.csv',b'wrong;header\n1;2')})
        self.assertContains(r,'Colunas obrigatórias ausentes')
        output=io.BytesIO()
        with ZipFile(output,'w') as z:z.writestr('../never-extracted.csv',self.df.head(1)[COLUMNS].to_csv(sep=';',index=False))
        output.seek(0)
        self.assertEqual(len(read_file(output,'base.zip')),1)
        r=self.client.post('/upload/',{'arquivo':SimpleUploadedFile('script.py',b'print(1)')})
        self.assertContains(r,'Extensão inválida')

    def test_filter_state_and_pb_scope(self):
        self.client.get('/',{'uf':'PE','aplicar':'1'})
        r=self.client.get('/temporal/')
        self.assertEqual(r.context['params']['uf'],'PE')
        self.assertEqual(r.context['rows'],len(self.df.loc[self.df.uf.eq('PE')]))
        r=self.client.get('/paraiba/')
        self.assertEqual(r.context['rows'],1358)
        exported=self.client.get('/exportar/csv/',{'contexto':'paraiba'})
        rows=pd.read_csv(io.BytesIO(exported.content),sep=';')
        self.assertTrue(rows.uf.eq('PB').all())
        self.client.get('/?limpar=1')
        self.assertEqual(self.client.get('/').context['rows'],len(self.df))

    def test_absent_data_message(self):
        with patch('dashboard.views.load',side_effect=FileNotFoundError('Base ausente')):
            self.assertContains(self.client.get('/'),'Base ausente')

    def test_presentation_and_detailed_modes_keep_same_totals(self):
        simple=self.client.get('/')
        self.assertEqual(simple.context['chart_mode'],'simples')
        self.assertEqual(len(simple.context['figures']),4)
        for chart in simple.context['figures']:
            self.assertTrue(all(trace['type'] in ['bar','scatter','pie'] for trace in chart['figure']['data']))
            for trace in chart['figure']['data']:
                if trace['type']=='bar' and trace.get('orientation')=='h':
                    self.assertLessEqual(len(trace['y']),5)
        pie=next(trace for chart in simple.context['figures'] for trace in chart['figure']['data'] if trace['type']=='pie')
        self.assertEqual(sum(pie['values']),simple.context['rows'])
        self.assertLessEqual(len(pie['labels']),5)
        detailed=self.client.get('/',{'visual':'detalhado'})
        self.assertEqual(len(detailed.context['figures']),8)
        self.assertEqual(simple.context['kpis'],detailed.context['kpis'])
        self.assertEqual(simple.context['rows'],detailed.context['rows'])
        self.assertEqual(self.client.get('/temporal/').context['chart_mode'],'detalhado')
        self.assertEqual(self.client.get('/',{'visual':'simples'}).context['chart_mode'],'simples')

    def test_offline_html_data_preserves_categories_and_unknown_counts(self):
        from dashboard.management.commands.exportar_html import browser_data
        sample=self.df.head(3).copy()
        sample.loc[sample.index[0],'mortos']=float('nan')
        sample.loc[sample.index[1],'municipio']=pd.NA
        original=sample.copy(deep=True)
        payload=browser_data(sample)
        self.assertEqual(payload['count'],3)
        self.assertIsNone(payload['metrics']['mortos'][0])
        self.assertEqual(payload['categories']['municipio']['codes'][1],-1)
        for column in payload['categories'].values():
            self.assertEqual(len(column['codes']),3)
        self.assertEqual(payload['dates'],sample.data_inversa.dt.strftime('%Y-%m-%d').tolist())
        for row in [0,1,2]:
            uf=payload['categories']['uf']
            self.assertEqual(uf['values'][uf['codes'][row]],sample.iloc[row].uf)
        pd.testing.assert_frame_equal(sample,original)
