const video = document.getElementById("video");
const canvas = document.getElementById("canvas");

const statusText = document.getElementById("statusText");
const decisionText = document.getElementById("decisionText");
const messageText = document.getElementById("messageText");
const overlayStatus = document.getElementById("overlayStatus");

let stream = null;
let detectionInterval = null;
let isSending = false;

let audioUnlocked = false;

// 🔴 speech control
let lastSpeechKey = "";
let lastSpeechTime = 0;
const SPEAK_GAP_MS = 5000;


// ================= AUDIO UNLOCK =================
function unlockAudio() {
  if (audioUnlocked) return;

  audioUnlocked = true;

  window.speechSynthesis.cancel();

  const test = new SpeechSynthesisUtterance("Audio ready");
  test.lang = "en-US";
  test.volume = 1;
  test.rate = 1.0;

  window.speechSynthesis.speak(test);
}


// ================= STATUS =================
function setStatus(text) {
  if (statusText) statusText.textContent = text;
  if (overlayStatus) overlayStatus.textContent = text;
}


// ================= CAMERA =================
async function startCamera() {
  try {
    setStatus("Requesting camera permission...");

    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
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


// ================= FRAME CAPTURE =================
function captureFrame() {
  const context = canvas.getContext("2d");

  const targetWidth = 320;
  const scale = targetWidth / video.videoWidth;
  const targetHeight = Math.round(video.videoHeight * scale);

  canvas.width = targetWidth;
  canvas.height = targetHeight;

  context.drawImage(video, 0, 0, targetWidth, targetHeight);

  return canvas.toDataURL("image/jpeg", 0.45);
}


// ================= SEND FRAME =================
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

    const decision = result.final_decision || result.decision || "---";
    const message =
      result.final_message ||
      result.message ||
      "No guidance available";

    if (decisionText) decisionText.textContent = decision;
    if (messageText) messageText.textContent = message;

    setStatus("Guidance active");

    speakMessage(message);

  } catch (error) {
    console.error("Send frame error:", error);
    setStatus("Connection error");

  } finally {
    isSending = false;
  }
}


// ================= SPEECH CONTROL =================
function cleanMessage(message) {
  return String(message || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}


function speakMessage(message) {
  if (!message) return;
  if (!audioUnlocked) return;

  const now = Date.now();
  const speechKey = cleanMessage(message);

  // ❌ SAME MESSAGE within 5 seconds → ignore
  if (speechKey === lastSpeechKey && now - lastSpeechTime < SPEAK_GAP_MS) {
    return;
  }

  // ❌ ANY speech too soon → ignore
  if (now - lastSpeechTime < SPEAK_GAP_MS) {
    return;
  }

  speakNow(message);

  lastSpeechKey = speechKey;
  lastSpeechTime = now;
}


function speakNow(message) {
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(message);
  utterance.lang = "en-US";
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.volume = 1.0;

  window.speechSynthesis.speak(utterance);
}


// ================= LOOP =================
async function detectionLoop() {
  while (video.srcObject) {
    await sendFrame();
    await new Promise((r) => setTimeout(r, 150));
  }
}


function startDetection() {
  if (detectionInterval) return;

  detectionInterval = true;
  detectionLoop();
}


// ================= EVENTS =================
document.addEventListener("DOMContentLoaded", () => {
  document.body.addEventListener("click", unlockAudio, { once: true });
  document.body.addEventListener("touchstart", unlockAudio, { once: true });
});


window.addEventListener("load", () => {
  startCamera();
});