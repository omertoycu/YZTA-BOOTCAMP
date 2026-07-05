import { useEffect, useRef, useState } from "react";

const RECORDER_MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function pickRecorderMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return RECORDER_MIME_CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type));
}

export type RecorderStage = "idle" | "recording" | "recorded";

/** Tarayıcıda mikrofonla sesli not kaydı almak için paylaşılan mantık —
 * /assistant (Voice-to-Listing) ve aday kartlarındaki sesli görüşme notu
 * panelinde aynı kayıt/yükleme akışı kullanılıyor. */
export function useAudioRecorder() {
  const [stage, setStage] = useState<RecorderStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [recordSeconds, setRecordSeconds] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop());
    };
  }, []);

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickRecorderMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const extension = (recorder.mimeType || "audio/webm").includes("mp4") ? "mp4" : "webm";
        setAudioFile(new File([blob], `sesli-not.${extension}`, { type: blob.type }));
        setAudioUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setStage("recording");
      setRecordSeconds(0);
      timerRef.current = setInterval(() => setRecordSeconds((s) => s + 1), 1000);
    } catch {
      setError("Mikrofona erişilemedi. Tarayıcı izinlerini kontrol edin ya da bir ses dosyası yükleyin.");
    }
  }

  function stop() {
    if (timerRef.current) clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
    setStage("recorded");
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setAudioFile(file);
    setAudioUrl(URL.createObjectURL(file));
    setStage("recorded");
  }

  function reset() {
    setStage("idle");
    setAudioFile(null);
    setAudioUrl(null);
    setError(null);
    setRecordSeconds(0);
  }

  return {
    stage,
    error,
    setError,
    audioUrl,
    audioFile,
    recordSeconds,
    start,
    stop,
    handleFileUpload,
    reset,
  };
}
