import os
import datetime
from django import forms


class GradeForm(forms.Form):
    student_name = forms.CharField(
        max_length=200,
        label='ФИО студента',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Иванов Иван Иванович',
        }),
    )
    subject = forms.CharField(
        max_length=200,
        label='Предмет',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    grade = forms.IntegerField(
        min_value=2,
        max_value=5,
        label='Оценка',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 2,
            'max': 5,
        }),
    )
    date = forms.DateField(
        label='Дата (ДД.ММ.ГГГГ)',
        input_formats=['%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '15.05.2024',
            'autocomplete': 'off',
        }),
    )
    file_format = forms.ChoiceField(
        choices=[('json', 'JSON'), ('xml', 'XML')],
        label='Формат файла',
        widget=forms.RadioSelect,
    )

    def clean_student_name(self):
        name = self.cleaned_data['student_name'].strip()
        if len(name) < 3:
            raise forms.ValidationError('ФИО слишком короткое.')
        if any(ch.isdigit() for ch in name):
            raise forms.ValidationError('ФИО не должно содержать цифр.')
        return name

    def clean_subject(self):
        subject = self.cleaned_data['subject'].strip()
        if len(subject) < 2:
            raise forms.ValidationError('Название предмета слишком короткое.')
        return subject

    def clean_date(self):
        d = self.cleaned_data['date']
        today = datetime.date.today()
        if d > today:
            raise forms.ValidationError('Дата не может быть в будущем.')
        if d.year < 2000:
            raise forms.ValidationError('Дата слишком старая.')
        return d


class UploadForm(forms.Form):
    file = forms.FileField(
        label='Файл (JSON или XML)',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.json,.xml',
        }),
    )

    def clean_file(self):
        f = self.cleaned_data['file']
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Файл больше 5 МБ.')
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in ('.json', '.xml'):
            raise forms.ValidationError('Допустимы только файлы .json и .xml.')
        return f