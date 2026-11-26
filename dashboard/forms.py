from django import forms
from .services.data_loader import MAX_SIZE


class UploadForm(forms.Form):
    arquivo = forms.FileField(label='Base DATATRAN (CSV, XLSX ou ZIP)')

    def clean_arquivo(self):
        file = self.cleaned_data['arquivo']
        if file.size > MAX_SIZE:
            raise forms.ValidationError('O arquivo deve ter no máximo 30 MB.')
        if not file.name.lower().endswith(('.csv','.xlsx','.zip')):
            raise forms.ValidationError('Extensão inválida. Use CSV, XLSX ou ZIP.')
        return file
