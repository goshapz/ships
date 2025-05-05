from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename  # Добавьте этот импорт
import os
import json
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from ultralytics import YOLO
import cv2  # Также добавьте этот импорт, если используете OpenCV

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['HISTORY_FILE'] = 'history.json'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'mp4'}

# Загрузка модели YOLO
model = YOLO('yolov8n.pt')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_to_history(ship_count):
    """Сохранение данных в историю"""
    entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ship_count': ship_count
    }

    # Создаем файл, если его нет
    if not os.path.exists(app.config['HISTORY_FILE']):
        with open(app.config['HISTORY_FILE'], 'w') as f:
            json.dump([], f)

    # Читаем существующую историю
    with open(app.config['HISTORY_FILE'], 'r') as f:
        history = json.load(f)

    # Добавляем новую запись
    history.append(entry)

    # Сохраняем обновленную историю
    with open(app.config['HISTORY_FILE'], 'w') as f:
        json.dump(history, f, indent=4)


def generate_pdf_report():
    """Генерация PDF отчета из истории"""
    if not os.path.exists(app.config['HISTORY_FILE']):
        return None

    # Читаем историю
    with open(app.config['HISTORY_FILE'], 'r') as f:
        history = json.load(f)

    # Создаем PDF в памяти
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Заголовок
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "Report")

    # Дата генерации
    c.setFont("Helvetica", 12)
    c.drawString(100, 770, f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Данные
    y_position = 730
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_position, "Datetime")
    c.drawString(250, y_position, "Ship count")
    y_position -= 20

    c.setFont("Helvetica", 10)
    for entry in history[-10:]:  # Последние 10 записей
        c.drawString(100, y_position, entry['timestamp'])
        c.drawString(250, y_position, str(entry['ship_count']))
        y_position -= 20

    # Статистика
    ship_counts = [entry['ship_count'] for entry in history]
    if ship_counts:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y_position - 30, "statistics:")
        c.setFont("Helvetica", 10)
        c.drawString(100, y_position - 50, f"count of entries: {len(history)}")
        c.drawString(100, y_position - 70, f"average: {sum(ship_counts) / len(ship_counts):.1f}")
        c.drawString(100, y_position - 90, f"max: {max(ship_counts)}")
        c.drawString(100, y_position - 110, f"min: {min(ship_counts)}")

    c.save()
    buffer.seek(0)
    return buffer


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Файл не выбран'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Файл не выбран'})

    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filename)

        # Обработка изображения
        results = model(filename)
        ship_count = sum(1 for box in results[0].boxes if box.cls == 8)

        # Сохранение в историю
        save_to_history(ship_count)

        # Визуализация результатов
        annotated_image = results[0].plot()
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_' + os.path.basename(filename))
        cv2.imwrite(output_path, annotated_image)

        return jsonify({
            'success': True,
            'result_url': f'/static/uploads/{os.path.basename(output_path)}',
            'ship_count': ship_count
        })

    return jsonify({'success': False, 'error': 'Неподдерживаемый формат'})


@app.route('/report')
def download_report():
    """Эндпоинт для скачивания PDF отчета"""
    pdf_buffer = generate_pdf_report()
    if not pdf_buffer:
        return jsonify({'success': False, 'error': 'Нет данных для отчета'})

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name='ship_report.pdf',
        mimetype='application/pdf'
    )


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)