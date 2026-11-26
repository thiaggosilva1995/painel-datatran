from django.db import models


class Importacao(models.Model):
    nome = models.CharField(max_length=255)
    arquivo = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64)
    criado = models.DateTimeField(auto_now_add=True)
    relatorio = models.JSONField(default=dict)
    status = models.CharField(max_length=30, default='prévia')
