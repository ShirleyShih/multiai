let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let stream;

async function recording() {
    if (!isRecording) {
        // 開始錄音
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        isRecording = true;

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        document.querySelector('.request-voice').src = '/static/img/stop.png';
    } else {
        // 停止錄音並處理音頻數據
        mediaRecorder.stop();
        isRecording = false;

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('file', audioBlob, 'audio.wav');

            const response = await fetch('/api/recording', {
                method: 'POST',
                body: formData,
            });

            const result = await response.json();
            console.log('Transcription:', result.transcription);
            document.getElementById("request").value=result.transcription;

            // 釋放麥克風訪問權限
            stream.getTracks().forEach(track => track.stop());

            audioChunks = [];
            document.querySelector('.request-voice').src = '/static/img/voice.png';
        };
    }
};