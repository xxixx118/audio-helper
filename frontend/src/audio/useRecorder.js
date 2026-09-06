import { useCallback, useEffect, useRef, useState } from "react";
import {
  MAX_DURATION_MS,
  MAX_FILE_BYTES,
  MIN_DURATION_MS,
  describeMediaError,
  detectSupportedMimeType,
} from "./recordSupport.js";

function stopStream(stream) {
  if (!stream) {
    return;
  }
  stream.getTracks().forEach((track) => {
    track.stop();
  });
}

export function useRecorder() {
  const [status, setStatus] = useState("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [recording, setRecording] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [supportedMimeType, setSupportedMimeType] = useState(detectSupportedMimeType);

  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const startedAtRef = useRef(0);
  const maxTimerRef = useRef(0);
  const tickTimerRef = useRef(0);
  const objectUrlRef = useRef("");
  const discardRef = useRef(false);
  const stopRequestedRef = useRef(false);
  const stoppingRef = useRef(false);
  const mimeTypeRef = useRef("");

  const clearTimers = useCallback(() => {
    window.clearTimeout(maxTimerRef.current);
    window.clearInterval(tickTimerRef.current);
    maxTimerRef.current = 0;
    tickTimerRef.current = 0;
  }, []);

  const revokeObjectUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = "";
    }
  }, []);

  const releaseMicrophone = useCallback(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
  }, []);

  const requestRecorderStop = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || stoppingRef.current || recorder.state !== "recording") {
      return false;
    }
    stoppingRef.current = true;
    recorder.stop();
    return true;
  }, []);

  const finishRecorder = useCallback(() => {
    clearTimers();
    const recorder = recorderRef.current;
    recorderRef.current = null;
    releaseMicrophone();

    if (discardRef.current) {
      discardRef.current = false;
      chunksRef.current = [];
      setElapsedMs(0);
      setStatus("idle");
      return;
    }

    const mimeType = mimeTypeRef.current || "audio/webm";
    const blob = new Blob(chunksRef.current, { type: mimeType });
    chunksRef.current = [];
    const durationMs = Date.now() - startedAtRef.current;

    if (durationMs < MIN_DURATION_MS) {
      setErrorMessage("录音时长需在1到60秒之间，请重新录制。");
      setStatus("error");
      setRecording(null);
      return;
    }

    if (blob.size > MAX_FILE_BYTES) {
      setErrorMessage("录音文件不能超过5MB，请缩短录音后重试。");
      setStatus("error");
      setRecording(null);
      return;
    }

    revokeObjectUrl();
    const url = URL.createObjectURL(blob);
    objectUrlRef.current = url;
    setRecording({
      blob,
      url,
      mimeType,
      durationMs: Math.min(durationMs, MAX_DURATION_MS),
      size: blob.size,
    });
    setErrorMessage("");
    setStatus("ready");
  }, [clearTimers, releaseMicrophone, revokeObjectUrl]);

  const startRecording = useCallback(async () => {
    const mimeType = detectSupportedMimeType();
    setSupportedMimeType(mimeType);
    if (!mimeType) {
      setErrorMessage("当前浏览器无法录制 WebM/Opus，请更换浏览器。");
      setStatus("error");
      return;
    }

    discardRef.current = false;
    stopRequestedRef.current = false;
    stoppingRef.current = false;
    setErrorMessage("");
    setElapsedMs(0);

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      setErrorMessage(describeMediaError(error));
      setStatus("error");
      return;
    }

    if (discardRef.current) {
      stopStream(stream);
      setStatus("idle");
      return;
    }

    if (stopRequestedRef.current) {
      stopStream(stream);
      setErrorMessage("录音时长需在1到60秒之间，请重新录制。");
      setStatus("error");
      return;
    }

    mimeTypeRef.current = mimeType;
    streamRef.current = stream;
    chunksRef.current = [];

    let recorder;
    try {
      recorder = new MediaRecorder(stream, { mimeType });
    } catch (error) {
      stopStream(stream);
      streamRef.current = null;
      setErrorMessage(describeMediaError(error));
      setStatus("error");
      return;
    }

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };
    recorder.onerror = () => {
      discardRef.current = true;
      setErrorMessage("录制失败，请重新按住按钮录音。");
      setStatus("error");
      if (recorder.state !== "inactive") {
        requestRecorderStop();
      } else {
        releaseMicrophone();
      }
    };
    recorder.onstop = () => {
      finishRecorder();
    };

    recorderRef.current = recorder;
    startedAtRef.current = Date.now();
    setStatus("recording");
    recorder.start();

    tickTimerRef.current = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAtRef.current);
    }, 100);

    maxTimerRef.current = window.setTimeout(() => {
      requestRecorderStop();
    }, MAX_DURATION_MS);

    if (stopRequestedRef.current || discardRef.current) {
      requestRecorderStop();
    }
  }, [finishRecorder, releaseMicrophone, requestRecorderStop]);

  const stopRecording = useCallback(() => {
    stopRequestedRef.current = true;
    if (requestRecorderStop()) {
      return;
    }
    if (!recorderRef.current && streamRef.current) {
      releaseMicrophone();
      setErrorMessage("录音时长需在1到60秒之间，请重新录制。");
      setStatus("error");
    }
  }, [releaseMicrophone, requestRecorderStop]);

  const cancelRecording = useCallback(() => {
    discardRef.current = true;
    stopRequestedRef.current = true;
    if (requestRecorderStop()) {
      return;
    }
    clearTimers();
    releaseMicrophone();
    chunksRef.current = [];
    setElapsedMs(0);
    setStatus((current) => (current === "recording" ? "idle" : current));
  }, [clearTimers, releaseMicrophone, requestRecorderStop]);

  useEffect(() => {
    function handleVisibility() {
      if (document.hidden) {
        cancelRecording();
      }
    }

    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      cancelRecording();
      revokeObjectUrl();
    };
  }, [cancelRecording, revokeObjectUrl]);

  return {
    status,
    errorMessage,
    recording,
    elapsedMs,
    supportedMimeType,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
