const recordButton = document.querySelector("#recordButton");
const recordLabel = document.querySelector("#recordLabel");
const polishButton = document.querySelector("#polishButton");
const copyButton = document.querySelector("#copyButton");
const clearButton = document.querySelector("#clearButton");
const styleSelect = document.querySelector("#styleSelect");
const transcriptEl = document.querySelector("#transcript");
const polishedEl = document.querySelector("#polished");
const statusEl = document.querySelector("#status");
const wordCountEl = document.querySelector("#wordCount");
const modelBadge = document.querySelector("#modelBadge");

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let isRecording = false;
let finalTranscript = "";

function setStatus(text) {
  statusEl.textContent = text;
}

function updateWordCount() {
  const text = transcriptEl.value.replace(/\s/g, "");
  wordCountEl.textContent = `${text.length} 字`;
}

function normalizeTranscript(text) {
  return text.replace(/\s+/g, " ").replace(/ ([，。！？、])/g, "$1").trim();
}

function setupRecognition() {
  if (!SpeechRecognition) {
    setStatus("当前浏览器不可用");
    recordButton.disabled = true;
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "zh-CN";
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isRecording = true;
    recordButton.setAttribute("aria-pressed", "true");
    recordLabel.textContent = "停止";
    setStatus("正在听");
  };

  recognition.onresult = (event) => {
    let interim = "";
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const result = event.results[index];
      if (result.isFinal) {
        finalTranscript += result[0].transcript;
      } else {
        interim += result[0].transcript;
      }
    }
    transcriptEl.value = normalizeTranscript(`${finalTranscript}${interim}`);
    updateWordCount();
  };

  recognition.onerror = (event) => {
    setStatus(event.error === "not-allowed" ? "麦克风未授权" : "听写中断");
  };

  recognition.onend = () => {
    isRecording = false;
    recordButton.setAttribute("aria-pressed", "false");
    recordLabel.textContent = "开始";
    finalTranscript = transcriptEl.value;
    setStatus("待整理");
  };
}

async function polishTranscript() {
  const transcript = transcriptEl.value.trim();
  if (!transcript) {
    setStatus("没有文本");
    return;
  }

  polishButton.disabled = true;
  setStatus("整理中");
  modelBadge.textContent = "处理中";

  try {
    const response = await fetch("/api/polish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript, style: styleSelect.value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "整理失败");
    }
    polishedEl.value = payload.text || "";
    modelBadge.textContent = payload.offline ? "本地" : payload.model || "AI";
    setStatus(payload.offline ? "本地整理完成" : "整理完成");
  } catch (error) {
    setStatus(error.message);
  } finally {
    polishButton.disabled = false;
  }
}

recordButton.addEventListener("click", () => {
  if (!recognition) return;
  if (isRecording) {
    recognition.stop();
  } else {
    finalTranscript = transcriptEl.value;
    recognition.start();
  }
});

polishButton.addEventListener("click", polishTranscript);

copyButton.addEventListener("click", async () => {
  const text = polishedEl.value || transcriptEl.value;
  if (!text.trim()) {
    setStatus("没有文本");
    return;
  }
  await navigator.clipboard.writeText(text);
  setStatus("已复制");
});

clearButton.addEventListener("click", () => {
  if (isRecording && recognition) recognition.stop();
  finalTranscript = "";
  transcriptEl.value = "";
  polishedEl.value = "";
  modelBadge.textContent = "本地";
  updateWordCount();
  setStatus("待命");
});

transcriptEl.addEventListener("input", () => {
  finalTranscript = transcriptEl.value;
  updateWordCount();
});

setupRecognition();
updateWordCount();
