export const MIN_DURATION_MS = 1000;
export const MAX_DURATION_MS = 60_000;
export const MAX_FILE_BYTES = 5 * 1024 * 1024;

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm"];

export function detectSupportedMimeType() {
  if (
    typeof MediaRecorder === "undefined" ||
    typeof MediaRecorder.isTypeSupported !== "function"
  ) {
    return null;
  }
  return MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) ?? null;
}

export function extensionForMimeType(mimeType) {
  if (mimeType && mimeType.includes("webm")) {
    return "webm";
  }
  return "webm";
}

export function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 100));
  const tenths = totalSeconds % 10;
  const seconds = Math.floor(totalSeconds / 10);
  return `${seconds}.${tenths} 秒`;
}

export function formatFileSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export function describeMediaError(error) {
  const name = error?.name || "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return "无法使用麦克风，请允许浏览器访问麦克风后重试。";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "未找到可用的麦克风，请检查设备后重试。";
  }
  if (name === "NotReadableError" || name === "TrackStartError") {
    return "麦克风被占用或无法启动，请关闭其他占用设备的应用后重试。";
  }
  return "录制失败，请重新按住按钮录音。";
}
