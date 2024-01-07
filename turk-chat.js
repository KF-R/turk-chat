// v0.7.0
// TODO: Ignore audio level trigger unless: flagged as ALWAYS_READY, ready_button/PTT is held down, or face detected and looking into camera
let audioContext;
let isRecording = false;
let isProcessing = false; // Flag to indicate audio processing is ongoing
let isAboveThreshold = false;
let ringBuffer = [];
let ringBufferHead = 0;
let startMarker = 0;
let endMarker = 0;
let endPersistCounter = 0;
let startTime = 0;
const END_PERSIST_PERIOD = 20; // How long to ignore silence when determining end of audio
const BUFFER_SIZE = 4096;
const PRE_ROLL = BUFFER_SIZE * 3; // Amount of preroll before the threshold is crossed
const SAMPLE_RATE = 48000; // or use audioContext.sampleRate
const THRESHOLD = 0.04; // Microphone volume threshold for speech detection
const BUFFER_DURATION = 60; // seconds
const MAX_RING_BUFFER_LENGTH = SAMPLE_RATE * BUFFER_DURATION; // Total samples for the duration
const ENDPOINT = '/upload'
const statusDiv = document.getElementById('status');


const RETRY_TIMEOUT = 1000 // Keep checking for responses at this frequency if first check failed
const RESPONSE_DELAY = 5000 // How long to wait before checking for a response after submission
const RESPONSE_FETCH_RETRY_LIMIT = 120 // How many times to check for a response before giving up.

const MESSAGE_LOG_FILENAME = 'messages.json'
const ENGINE_LOG_FILENAME = 'turk_flask.log'
const ENGINE_LOG_LINES_LIMIT = 20 // How much of the engine log tail to show

window.addEventListener('load', function() {
    fetchVoiceList();
    loadAndDisplayChatLog(MESSAGE_LOG_FILENAME);
    loadAndDisplayEngineLog(ENGINE_LOG_FILENAME);
    scanner_paused = true;
    // document.getElementById('iq-switch').checked=true;
});

function initAudioContext() {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
}

function startRecording() {
    if (!audioContext) {
        initAudioContext();
    }

    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            isRecording = true;
            let microphone = audioContext.createMediaStreamSource(stream);
            let scriptProcessor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);
            microphone.connect(scriptProcessor);
            scriptProcessor.connect(audioContext.destination);
            scriptProcessor.onaudioprocess = processAudio;
            updateStatus("Listening...", [1, 0, 0], 75, 'Kitt');

            document.getElementById("startButton").style.visibility = "hidden";
            document.getElementById("startButton").disabled = true; 

            document.getElementById("stopButton").style.visibility = "visible";
            document.getElementById("stopButton").disabled = false; 

        }).catch(err => {
            console.error("Error accessing microphone", err);
        });
}

function processAudio(audioProcessingEvent) {
    if (!isRecording || isProcessing) return; // Don't process new audio if currently processing or not recording

    let inputData = audioProcessingEvent.inputBuffer.getChannelData(0);
    let sum = 0;

    for (let i = 0; i < inputData.length; ++i) {
        sum += inputData[i] * inputData[i];
        ringBuffer[ringBufferHead] = inputData[i]; // Save data to ring buffer
        ringBufferHead = (ringBufferHead + 1) % MAX_RING_BUFFER_LENGTH; // Circular increment
    }

    let volume = Math.sqrt(sum / inputData.length);
    detectSound(volume);
}

function detectSound(volume) {
    if (volume > THRESHOLD && !isAboveThreshold) {
        isAboveThreshold = true;
        startMarker = (ringBufferHead + MAX_RING_BUFFER_LENGTH - PRE_ROLL) % MAX_RING_BUFFER_LENGTH;
        startTime = Date.now();
        updateStatus("Sound detected...", [0, 1, 0], 75, 'Cylon');

    } else if (volume < THRESHOLD && isAboveThreshold) {
        if (endPersistCounter >= END_PERSIST_PERIOD) {
            isAboveThreshold = false;
            endMarker = ringBufferHead;
            let length = (endMarker - startMarker + MAX_RING_BUFFER_LENGTH) % MAX_RING_BUFFER_LENGTH;
            let audioData = new Float32Array(length);

            for (let i = 0; i < length; i++) {
                audioData[i] = ringBuffer[(startMarker + i) % MAX_RING_BUFFER_LENGTH];
            }

            let audioBuffer = audioContext.createBuffer(1, audioData.length, SAMPLE_RATE);
            audioBuffer.copyToChannel(audioData, 0);

            isRecording = false; 
            isProcessing = true;
            convertToWav(audioBuffer, startTime);
            updateStatus("Silence detected, processing...", [1, 0, 1], 60, 'Cylon');

            endPersistCounter = 0;
        } else {
            endPersistCounter++;
        }
    }
}

function convertToWav(audioBuffer, label) {
    let numChannels = audioBuffer.numberOfChannels;
    let numSamples = audioBuffer.length;
    let buffer = new ArrayBuffer(44 + numSamples * 2 * numChannels);
    let view = new DataView(buffer);

    function writeDataString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    // Writing the WAV container
    writeDataString(view, 0, 'RIFF');
    view.setUint32(4, 36 + numSamples * 2, true);
    writeDataString(view, 8, 'WAVE');
    writeDataString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, SAMPLE_RATE, true);
    view.setUint32(28, SAMPLE_RATE * numChannels * 2, true);
    view.setUint16(32, numChannels * 2, true);
    view.setUint16(34, 16, true);
    writeDataString(view, 36, 'data');
    view.setUint32(40, numSamples * 2, true);

    let index = 44;
    let volume = 1;
    for (let i = 0; i < numSamples; i++) {
        view.setInt16(index, audioBuffer.getChannelData(0)[i] * (0x7FFF * volume), true);
        index += 2;
    }

    let blob = new Blob([view], { type: 'audio/wav' });
    
    let formData = new FormData();
    formData.append("audio", blob, label + '.wav');

    let selectedName = document.getElementById('nameDropdown').value;
    formData.append("name", selectedName);

    var iqValue = document.getElementById('iq-switch').checked ? 'on' : 'off';
    formData.set('advanced_model', iqValue);

    fetch(ENDPOINT, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        updateStatus('File uploaded successfully!', [1, 0, 0], 20, 'Cylon');

        loadAndPlayMP3(`${label}`.substring(0,10) + '.mp3').then(() => {
            // After playback is complete, resume listening
            isRecording = true;
            isProcessing = false;
            updateStatus("Listening...", [1, 0, 0], 75);
        });

    })
    .catch((error) => {
        console.error('Error:', error);
        updateStatus('Failed to upload file.', [1, 1, 0], 5, 'Cylon');
        isRecording = true;
        isProcessing = false;
    });
}

function updateStatus(message, new_scanner_colour = [1, 0, 0], new_scanner_speed = 75, new_scanner_mode = 'Kitt') {
    statusDiv.innerText = message;
    statusDiv.style.backgroundColor = isRecording ? "green" : "grey";

    scanner_colour_flags = new_scanner_colour
    if (new_scanner_mode != scanner_mode) {
        changeMode(new_scanner_mode);
    }
    if (new_scanner_speed > 5) {
        scanner_speed = new_scanner_speed;
        scanner_paused = false;
    } else {
        scanner_paused = true;
    }
}

function formatReportString(input) {
    const parts = input.split('|'); // Assumes token and cost reports are on the same line, separated by a pipe
    
    if(parts.length === 2) {
        // Return the HTML string with left and right aligned spans
        return `<span style="float: left;">${parts[0].trim()}</span><span style="float: right;">${parts[1].trim()}</span>`;
    } else {
        // Return the original input if it doesn't contain a pipe character or is not split into two parts
        return input;
    }
}

function loadAndPlayMP3(mp3_filename) {
    return new Promise((resolve, reject) => {
        let hasPlayed = false;
        let attempts = 0;
        let audioContext = new (window.AudioContext || window.webkitAudioContext)();
        let analyser = audioContext.createAnalyser();

        function updateUIAfterPlayback() {
            document.getElementById('status').textContent = 'Playback finished';
            console.log('Playback finished');
            resolve(); // Resolve the promise indicating the MP3 has finished playing
        }

        const drawVUMeter = () => {

            requestAnimationFrame(drawVUMeter);
            let dataArray = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteFrequencyData(dataArray);

            let canvas = document.getElementById('vuMeter');
            if (canvas != null) {

                let ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                let barWidth = (canvas.width / dataArray.length);
                let barHeight;
                let x = 0;
                for(let i = 0; i < dataArray.length; i++) {
                    barHeight = dataArray[i]/2;
                    ctx.fillStyle = 'rgb(' + (barHeight+150) + ',50,50)';
                    ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

                    x += barWidth + 1;
                }
            } else {
                let mean = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
                let normalizedMean = (mean / 255) * 10; // Assuming the max value in dataArray is 255
                drawKittFrame(Math.floor(normalizedMean * 10));
            }
        };

        const tryFetch = () => {
            fetch(mp3_filename)
                .then(response => {
                    if(response.ok) return response.blob();
                    throw new Error('File not found');
                })
                .then(blob => {
                    let audioSrc = audioContext.createMediaElementSource(new Audio(URL.createObjectURL(blob)));
                    audioSrc.connect(analyser);
                    analyser.connect(audioContext.destination);

                    audioSrc.mediaElement.play();
                    hasPlayed = true;
                    drawVUMeter();

                    audioSrc.mediaElement.addEventListener('ended', updateUIAfterPlayback);

                    loadAndDisplayChatLog(MESSAGE_LOG_FILENAME)
                    loadAndDisplayEngineLog(ENGINE_LOG_FILENAME)
                    
                })
                .catch(error => {
                    console.error('Fetch failed', error);
                    reject(error);
                });
        };

        setTimeout(() => {
            tryFetch();
            let interval = setInterval(() => {
                if(!hasPlayed && attempts < RESPONSE_FETCH_RETRY_LIMIT) {
                    tryFetch();
                    attempts++;
                } else {
                    clearInterval(interval);
                }
            }, RETRY_TIMEOUT);
        }, RESPONSE_DELAY);
    });
}

function htmlCodeBlock(text) {
    // Converts triple back-tick delimiter pairs to html
    const regex = /```(.*?)```/gs;

    // Replace the matched pairs with <pre> and </pre> tags
    const convertedText = text.replace(regex, function(match, group1) {
        return `<pre>${group1}</pre>`;
    });

    return convertedText;
}

async function loadAndDisplayChatLog(message_log_filename) {
    chatLogElement = document.getElementById('messages');
    if (chatLogElement == null) return;

    try {
        const response = await fetch(message_log_filename);
        if (!response.ok) {
            console.warn('Failed to fetch chat log:');
            return;
        }

        const chatLog = await response.json();
        chatLog.reverse()

        let formattedHtml = '';
        chatLog.forEach(entry => {
            switch (entry.role) {
                case 'system':
                    formattedHtml += `<div class="message system-message"><pre>${entry.content}</pre></div>`;
                    break;
                case 'user':
                    formattedHtml += `<div class="message user-message">${entry.content}</div>`;
                    break;
                case 'assistant':
                    if (String(entry.content).includes("```")) {
                        formattedHtml += `<div class="message assistant-message">${htmlCodeBlock(entry.content)}</div>`;
                    } else {
                        formattedHtml += `<div class="message assistant-message">${entry.content}</div>`;
                    }
                    break;
                default:
                    formattedHtml += `<div class="message">${entry.content}</div>`;
            }
        });

        chatLogElement.innerHTML = formattedHtml;

    } catch (error) {
        console.error('Failed to parse chat log:', error);
    }
}

async function loadAndDisplayEngineLog(engine_log_filename) {
    engineLogElement = document.getElementById('engine-log');
    if (engineLogElement == null) return;

    try {
        const response = await fetch(engine_log_filename);
        if (!response.ok) {
            console.warn('Failed to fetch engine log.');
            return;
        }

        const engineLog = await response.text()

        var lines = engineLog.split('\n').slice(-ENGINE_LOG_LINES_LIMIT);
        lines.reverse();

        for (let i = 0; i < lines.length; i++) {
            lines[i] = formatReportString(lines[i]) + '<br/>\n'
        }

        var reversedOrderLog = lines.join('\n');

        engineLogElement.innerHTML= reversedOrderLog;

    } catch (error) {
        console.error('Failed to load engine log:', error);
    }    
}

async function fetchVoiceList() {
    try {
        const response = await fetch('voices');
        if (!response.ok) {
            console.warn('Failed to fetch voice list.');
            return;
        }

        const voiceList = await response.text();
        voices = JSON.parse(voiceList);
        voices.unshift('');
        
        const nameDropdown = document.getElementById('nameDropdown');

        for (const name of voices) {
            const option = document.createElement('option');
            option.value = name;
            option.text = name;
            option.selected = true;
            nameDropdown.appendChild(option);
        }
        
        // Set the first option as selected
        if (nameDropdown.options.length > 0) {
            nameDropdown.options.remove(0);
            nameDropdown.options[0].selected = true;
        }

    } catch (error) {
        console.error('Failed to parse TTS voice list.', error);
    }      
}

