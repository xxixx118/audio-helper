import { useEffect, useRef } from "react";

export function RecordButton({
  disabled,
  recording,
  elapsedLabel,
  onPressStart,
  onPressEnd,
  onCancel,
}) {
  const pointerIdRef = useRef(null);

  useEffect(() => {
    if (!recording) {
      return undefined;
    }

    function handleWindowPointerUp() {
      onPressEnd();
    }

    function handleWindowPointerCancel() {
      onCancel();
    }

    window.addEventListener("pointerup", handleWindowPointerUp);
    window.addEventListener("pointercancel", handleWindowPointerCancel);
    return () => {
      window.removeEventListener("pointerup", handleWindowPointerUp);
      window.removeEventListener("pointercancel", handleWindowPointerCancel);
    };
  }, [recording, onPressEnd, onCancel]);

  function releaseCapture(target) {
    if (pointerIdRef.current !== null && target.hasPointerCapture(pointerIdRef.current)) {
      target.releasePointerCapture(pointerIdRef.current);
    }
    pointerIdRef.current = null;
  }

  return (
    <button
      type="button"
      className={recording ? "record-button is-recording" : "record-button"}
      disabled={disabled}
      onContextMenu={(event) => event.preventDefault()}
      onPointerDown={(event) => {
        if (disabled || event.button !== 0) {
          return;
        }
        event.preventDefault();
        pointerIdRef.current = event.pointerId;
        event.currentTarget.setPointerCapture(event.pointerId);
        onPressStart();
      }}
      onPointerUp={(event) => {
        releaseCapture(event.currentTarget);
        onPressEnd();
      }}
      onPointerCancel={(event) => {
        releaseCapture(event.currentTarget);
        onCancel();
      }}
    >
      {recording ? `录音中 ${elapsedLabel}` : "按住说话"}
    </button>
  );
}
