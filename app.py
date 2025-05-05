from flask import Flask, render_template, request, jsonify
import os
import cv2
from ultralytics import YOLO
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'mp4'}

# Загружаем предобученную модель YOLOv8 (можно дообучить на своих данных)
model = YOLO('yolov8n.pt')  # 'yolov8s.pt' или 'yolov8m.pt' для большей точности


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_' + os.path.basename(video_path))
    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    total_ships = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Детекция
        results = model(frame)
        annotated_frame = results[0].plot()

        # Подсчёт кораблей в текущем кадре
        ship_count = sum(1 for box in results[0].boxes if box.cls == 8)
        total_ships = max(total_ships, ship_count)  # Или сумма по всем кадрам

        out.write(annotated_frame)

    cap.release()
    out.release()
    return output_path, total_ships

def process_image(image_path):
    # Детекция объектов
    results = model(image_path)

    # Визуализация результатов
    annotated_frame = results[0].plot()  # Рисуем bounding boxes

    # Сохраняем обработанное изображение
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_' + os.path.basename(image_path))
    cv2.imwrite(output_path, annotated_frame)

    # Подсчёт кораблей (класс 'ship' в COCO = 8)
    ship_count = sum(1 for box in results[0].boxes if box.cls == 8)

    return output_path, ship_count


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
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Обработка изображения/видео
        if filepath.endswith(('png', 'jpg', 'jpeg')):
            output_path, ship_count = process_image(filepath)
            return jsonify({
                'success': True,
                'result_url': f'/static/uploads/{os.path.basename(output_path)}',
                'ship_count': ship_count
            })
        elif filepath.endswith('mp4'):
            output_path, ship_count = process_video(filepath)
            return jsonify({
                'success': True,
                'result_url': f'/static/uploads/{os.path.basename(output_path)}',
                'ship_count': ship_count
            })

    return jsonify({'success': False, 'error': 'Неподдерживаемый формат'})


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)