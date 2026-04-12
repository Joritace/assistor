const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

const statusText = document.getElementById("statusText");
const decisionText = document.getElementById("decisionText");
const messageText = document.getElementById("messageText");
const overlayStatus = document.getElementById("overlayStatus");

let stream = null;
let detectionInterval = null;
let isSending = false;

let lastSpokenMessage = "";
let lastSpokenTime = 0;

function setStatus(text) {
  if (statusText) statusText.textContent = text;
  if (overlayStatus) overlayStatus.textContent = text;
}
// Initialize the camera and start the video stream
async function startCamera() {
  try {
    setStatus("Requesting camera permission...");

    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment"
      },
      audio: false
    });

    video.srcObject = stream;

    await new Promise((resolve) => {
      video.onloadedmetadata = () => resolve();
    });

    await video.play();

    setStatus("Guidance active");
    startDetection();
  } catch (error) {
    console.error("Camera error:", error);
    setStatus("Camera unavailable");
    if (messageText) {
      messageText.textContent = "Please allow camera access to begin navigation.";
    }
  }
}
// Capture the current video frame and return it as a base64-encoded JPEG image
function captureFrame() {
  const context = canvas.getContext("2d");

  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;

  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  return canvas.toDataURL("image/jpeg", 0.8);
}
// Send the captured frame to the ml service for prediction and handle the response
async function sendFrame() {
  if (isSending) return;
  if (!video.srcObject) return;

  try {
    isSending = true;
    setStatus("Analyzing environment...");

    const image = captureFrame();

    const response = await fetch("/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ image })
    });

    const result = await response.json();

    if (!result.ok) {
      console.error("Prediction error:", result.error);
      setStatus("Prediction failed");
      return;
    }

    const decision = result.decision || "---";
    const message = result.message || "No guidance available";
    const cooldown = result.cooldown || 3;

    if (decisionText) {
      decisionText.textContent = decision;
    }

    if (messageText) {
      messageText.textContent = message;
    }

    setStatus("Guidance active");
    speakMessage(message, cooldown);
  } catch (error) {
    console.error("Send frame error:", error);
    setStatus("Connection error");
  } finally {
    isSending = false;
  }
}

function speakMessage(message, cooldownSeconds = 3) {
  if (!message) return;

  const now = Date.now();
  const cooldownMs = cooldownSeconds * 1000;

  const repeatedTooSoon =
    message === lastSpokenMessage && now - lastSpokenTime < cooldownMs;

  if (repeatedTooSoon) {
    return;
  }

  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(message);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  window.speechSynthesis.speak(utterance);

  lastSpokenMessage = message;
  lastSpokenTime = now;
}

function startDetection() {
  if (detectionInterval) return;

  sendFrame();
  detectionInterval = setInterval(sendFrame, 400);
}

window.addEventListener("load", () => {
  startCamera();
});