import { useState } from "react";
import { getHealth } from "./api.js";

function App() {
  const [healthText, setHealthText] = useState("");

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

  return (
    <main className="page">
      <h1>语音约碰面地点</h1>
      <p>第一版骨架页。录音和找店功能尚未接入。</p>
      <p className="hint">页面默认城市：杭州（后续可改）</p>
      <button type="button" onClick={handleCheckHealth}>
        检查后端连接
      </button>
      {healthText ? <pre>{healthText}</pre> : null}
    </main>
  );
}

export default App;
