let currentMode = 'image';
let cameraStream = null;

// Выбор режима (изображение/видео/камера)
function setMode(mode) {
    currentMode = mode;
    document.getElementById('upload-section').style.display =
        (mode === 'camera') ? 'none' : 'block';
    document.getElementById('camera-section').style.display =
        (mode === 'camera') ? 'block' : 'none';
}

// Запуск камеры
function startCamera() {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            cameraStream = stream;
            const videoElement = document.getElementById('camera-stream');
            videoElement.srcObject = stream;
        })
        .catch(err => console.error("Ошибка камеры:", err));
}

// Остановка камеры
function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        document.getElementById('camera-stream').srcObject = null;
    }
}

function processMedia() {
    const fileInput = document.getElementById('file-input');
    const outputImage = document.getElementById('output-image');
    const outputCanvas = document.getElementById('output-canvas');
    const resultsDiv = document.getElementById('results');

    if (currentMode === 'image' || currentMode === 'video') {
        const file = fileInput.files[0];
        if (!file) {
            alert("Выберите файл!");
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        fetch('/process', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                outputImage.src = data.result_url;
                outputImage.style.display = 'block';
                resultsDiv.innerHTML = `
                    <h2>Результат:</h2>
                    <p>Количество судов: <strong>${data.ship_count}</strong></p>
                    <img src="${data.result_url}" style="max-width: 100%;">
                `;
            } else {
                alert("Ошибка: " + data.error);
            }
        });
    }
}