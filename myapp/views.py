import json
import os
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import GradeForm, UploadForm

DATA_DIR = os.path.join(settings.MEDIA_ROOT, 'data')
UPLOAD_DIR = os.path.join(settings.MEDIA_ROOT, 'uploads')

REQUIRED_FIELDS = ('student', 'subject', 'grade', 'date')


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def _validate_record(item, idx):
    for key in REQUIRED_FIELDS:
        if key not in item:
            raise ValueError(f'Запись #{idx}: отсутствует поле "{key}".')

    try:
        g = int(item['grade'])
    except (TypeError, ValueError):
        raise ValueError(f'Запись #{idx}: оценка должна быть числом.')

    if not 2 <= g <= 5:
        raise ValueError(f'Запись #{idx}: оценка должна быть от 2 до 5.')

    item['grade'] = g

    date_str = str(item['date']).strip()
    parsed = None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            parsed = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        raise ValueError(
            f'Запись #{idx}: дата должна быть в формате ДД.ММ.ГГГГ.'
        )

    item['date'] = parsed.strftime('%d.%m.%Y')
    return item


def parse_json_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError('Корневой элемент JSON должен быть массивом.')
    return [_validate_record(item, i) for i, item in enumerate(data, 1)]


def parse_xml_file(path):
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        raise ValueError(f'Ошибка разбора XML: {e}')
    root = tree.getroot()
    result = []
    for i, el in enumerate(root, 1):
        item = {child.tag: (child.text or '').strip() for child in el}
        result.append(_validate_record(item, i))
    return result


def load_records(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.json':
        return parse_json_file(path)
    if ext == '.xml':
        return parse_xml_file(path)
    raise ValueError('Неподдерживаемое расширение файла.')


def _list_files():
    files = []
    for folder, base in (('data', DATA_DIR), ('uploads', UPLOAD_DIR)):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if os.path.splitext(name)[1].lower() not in ('.json', '.xml'):
                continue
            full = os.path.join(base, name)
            files.append({
                'folder': folder,
                'name': name,
                'size': os.path.getsize(full),
                'mtime': datetime.fromtimestamp(os.path.getmtime(full)),
            })
    return files


def _append_record(record, fmt):
    if fmt == 'json':
        path = os.path.join(DATA_DIR, 'grades.json')
        records = []
        if os.path.isfile(path):
            try:
                records = parse_json_file(path)
            except ValueError:
                records = []
        records.append(record)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    else:
        path = os.path.join(DATA_DIR, 'grades.xml')
        records = []
        if os.path.isfile(path):
            try:
                records = parse_xml_file(path)
            except ValueError:
                records = []
        records.append(record)
        root = ET.Element('grades')
        for r in records:
            el = ET.SubElement(root, 'grade')
            for key in REQUIRED_FIELDS:
                ET.SubElement(el, key).text = str(r[key])
        ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def index(request):
    ensure_dirs()
    form = GradeForm()

    if request.method == 'POST':
        form = GradeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            record = {
                'student': data['student_name'],
                'subject': data['subject'],
                'grade': data['grade'],
                'date': data['date'].strftime('%d.%m.%Y'),
            }
            try:
                _append_record(record, data['file_format'])
                messages.success(
                    request,
                    f'Запись сохранена в grades.{data["file_format"]}'
                )
                return redirect('index')
            except Exception as e:
                messages.error(request, f'Не удалось сохранить: {e}')

    files = _list_files()
    return render(request, 'myapp/index.html', {'form': form, 'files': files})


def upload_view(request):
    ensure_dirs()
    form = UploadForm()

    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['file']
            ext = os.path.splitext(uploaded.name)[1].lower()

            safe_name = f'{uuid.uuid4().hex}{ext}'
            dest = os.path.join(UPLOAD_DIR, safe_name)

            with open(dest, 'wb+') as out:
                for chunk in uploaded.chunks():
                    out.write(chunk)

            try:
                load_records(dest)
            except Exception as e:
                os.remove(dest)
                messages.error(
                    request,
                    f'Файл "{uploaded.name}" не прошёл проверку и был удалён: {e}'
                )
                return redirect('upload')

            messages.success(
                request,
                f'Файл "{uploaded.name}" успешно загружен и прошёл проверку.'
            )
            return redirect('index')

    return render(request, 'myapp/upload.html', {'form': form})


def file_detail(request, folder, filename):
    ensure_dirs()
    base = {'data': DATA_DIR, 'uploads': UPLOAD_DIR}.get(folder)
    if base is None:
        messages.error(request, 'Неизвестный раздел.')
        return redirect('index')

    safe_name = os.path.basename(filename)
    path = os.path.join(base, safe_name)

    if not os.path.isfile(path):
        messages.error(request, 'Файл не найден.')
        return redirect('index')

    try:
        records = load_records(path)
    except Exception as e:
        messages.error(request, f'Не удалось прочитать файл: {e}')
        return redirect('index')

    return render(request, 'myapp/file_detail.html', {
        'filename': safe_name,
        'folder': folder,
        'records': records,
    })