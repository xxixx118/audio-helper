import { useEffect, useState } from "react";
import { getHealth } from "./api.js";
import { CitySelect } from "./components/CitySelect.jsx";
import { RecordButton } from "./components/RecordButton.jsx";
import {
  extensionForMimeType,
  formatDuration,
  formatFileSize,
} from "./audio/recordSupport.js";
import { useRecorder } from "./audio/useRecorder.js";

function App() {
  const [city, setCity] = useState("杭州");
  const [healthText, setHealthText] = useState("");
  const {
    status,
    errorMessage,
    recording,
    elapsedMs,
    supportedMimeType,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useRecorder();

  const formatUnsupported = supportedMimeType === null;
  const isRecording = status === "recording";

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        cancelRecording();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [cancelRecording]);

  async function handleCheckHealth() {
    try {
      const response = await getHealth();
      setHealthText(JSON.stringify(response.data, null, 2));
    } catch (error) {
      const message = error.response
        ? `请求失败：${error.response.status}`
        : "无法连接后端，请确认已在 8003 端口启动服务。";
      setHealthText(message);
    }
  }

  const downloadName = recording
    ? `meetup-recording.${extensionForMimeType(recording.mimeType)}`
    : "";

  return (
    <main className="page">
      <h1>语音约碰面地点</h1>
      <p>按住按钮录音，松开结束。本轮只做本地录音，不会上传或找店。</p>

      <CitySelect value={city} onChange={setCity} />

      <RecordButton
        disabled={formatUnsupported}
        recording={isRecording}
        elapsedLabel={formatDuration(elapsedMs)}
        onPressStart={startRecording}
        onPressEnd={stopRecording}
        onCancel={cancelRecording}
      />

      {formatUnsupported ? (
        <p className="error" role="alert">
          当前浏览器无法录制 WebM/Opus，请更换浏览器。
        </p>
      ) : (
        <p className="hint">
          请按住说话 1 到 60 秒。移出按钮后松开、按 Esc、或录满 60
          秒都会结束并释放麦克风。
        </p>
      )}

      {errorMessage ? (
        <p className="error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      {recording ? (
        <section className="recording-result">
          <h2>本地试听</h2>
          <audio controls src={recording.url} />
          <p className="hint">
            格式 {recording.mimeType}，大小 {formatFileSize(recording.size)}，时长{" "}
            {formatDuration(recording.durationMs)}
          </p>
          <a className="download-link" href={recording.url} download={downloadName}>
            下载录音文件（临时，供后续上传测试）
          </a>
        </section>
      ) : null}

      <section className="health-block">
        <button type="button" className="secondary-button" onClick={handleCheckHealth}>
          检查后端连接
        </button>
        {healthText ? <pre>{healthText}</pre> : null}
      </section>
    </main>
  );
}

export default App;
