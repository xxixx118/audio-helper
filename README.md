# 语音约碰面地点

按住录音，说出两个人的位置和想去的店，系统识别后查找同一座城市内、大致中点附近的候选店铺，并播报推荐。

当前进度：项目骨架。已实现后端 `GET /health` 和可打开的前端基础页。录音及其他业务接口尚未开发。

## 环境要求

- Python 3.11
- Node.js 22.12 及以上的 22.x
- 本机后续上传校验会用到 `ffprobe`（本轮健康检查不需要）

## 安装依赖

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` 中的密钥可以先留空。未填写时，健康检查仍应可用。

```bash
cd frontend
npm install
```

## 启动

后端（8003 端口）：

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8003
```

前端（5175 端口）：

```bash
cd frontend
npm run dev
```

CORS 仅放行 `http://localhost:5175`。

## 本轮如何验证

浏览器打开：

- 前端页：http://localhost:5175
- 健康检查：http://localhost:8003/health
- 接口文档：http://localhost:8003/docs ，在其中调用 `GET /health`

可选：在 `backend` 目录、已激活虚拟环境后执行：

```bash
pytest tests/test_health.py
```

Mock 测试通过不能证明真实厂商接口已跑通。真实 ASR、DeepSeek、高德、TTS 和前端全链路验收，等后续接口完成且你确认后再做。

## 约定端口

| 服务 | 地址 |
| --- | --- |
| 后端 | http://localhost:8003 |
| 前端 | http://localhost:5175 |
