"""Gera um snapshot tratado e seu relatório sem ativar ou alterar o CSV original."""
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from dashboard.services.data_loader import load
from dashboard.services.data_cleaning import COLUMNS


class Command(BaseCommand):
    help='Salva snapshot tratado e relatório de qualidade da base atual.'
    def handle(self,*args,**options):
        df,report=load()
        folder=settings.BASE_DIR/'data/processed';folder.mkdir(parents=True,exist_ok=True)
        df[COLUMNS].to_csv(folder/'datatran_tratado.csv',sep=';',index=False,encoding='utf-8-sig')
        (folder/'qualidade.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'{len(df)} sinistros tratados. Original preservado.'))
