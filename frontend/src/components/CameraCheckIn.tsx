import { useEffect, useRef, useState } from "react";
import api, { apiErrorMessage } from "../api/client";

// face-api pulls in TensorFlow.js (~1.8 MB). It is imported only when someone
// actually opens the camera, so it never lands in the main bundle.
type FaceApi = typeof import("@vladmandic/face-api");

type Phase = "idle" | "loading" | "ready" | "submitting" | "done";

const MODEL_URL = "/models";
const DETECT_INTERVAL_MS = 500;

export default function CameraCheckIn({ onCheckedIn }: { onCheckedIn: () => void }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const faceApiRef = useRef<FaceApi | null>(null);

  const [phase, setPhase] = useState<Phase>("idle");
  const [faces, setFaces] = useState(0);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  // Camera and geolocation are only available over HTTPS (localhost excepted).
  const secure = window.isSecureContext;

  useEffect(() => stop, []);

  function stop() {
    if (timerRef.current) window.clearInterval(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }

  async function start() {
    setError("");
    setNote("");
    setPhase("loading");
    try {
      const faceapi = faceApiRef.current ?? (await import("@vladmandic/face-api"));
      faceApiRef.current = faceapi;
      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 480 }, height: { ideal: 360 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setPhase("ready");

      const options = new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 });
      timerRef.current = window.setInterval(async () => {
        if (!videoRef.current || videoRef.current.readyState < 2) return;
        const found = await faceapi.detectAllFaces(videoRef.current, options);
        setFaces(found.length);
      }, DETECT_INTERVAL_MS);
    } catch (err) {
      setPhase("idle");
      setError(
        err instanceof Error && err.name === "NotAllowedError"
          ? "Camera permission was denied. Allow it in the browser and try again."
          : `Could not start the camera: ${err instanceof Error ? err.message : String(err)}`,
      );
    }
  }

  function getPosition(): Promise<GeolocationPosition> {
    return new Promise((resolve, reject) =>
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }),
    );
  }

  async function submit() {
    setError("");
    setNote("");
    setPhase("submitting");
    try {
      setNote("Getting your location…");
      const pos = await getPosition();

      setNote("Checking you in…");
      await api.post("/attendance/check-in", {
        source: "camera",
        face_detected: faces === 1,
        faces_count: faces,
        lat: pos.coords.latitude,
        lng: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      });

      stop();
      setPhase("done");
      setNote("");
      onCheckedIn();
    } catch (err) {
      setPhase("ready");
      setNote("");
      const geoErr = err as GeolocationPositionError;
      if (geoErr && typeof geoErr.code === "number" && geoErr.code === 1) {
        setError("Location permission was denied. Camera check-in needs it to confirm you are at the office.");
      } else if (geoErr && typeof geoErr.code === "number") {
        setError("Could not get your location. Move near a window or outdoors and try again.");
      } else {
        setError(apiErrorMessage(err));
      }
    }
  }

  if (!secure) {
    return (
      <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-4 text-sm">
        <div className="font-medium">Camera check-in needs HTTPS</div>
        <p className="mt-1">
          Browsers only allow the camera and location on a secure connection. Open this site over{" "}
          <code>https://</code> and the option will appear here.
        </p>
      </div>
    );
  }

  const faceOk = faces === 1;

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Camera check-in</h3>
        {phase === "ready" && (
          <span className={`text-xs rounded px-2 py-0.5 ${faceOk ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}>
            {faces === 0 ? "No face detected" : faces === 1 ? "Face detected" : `${faces} faces — only you should be visible`}
          </span>
        )}
      </div>

      {error && <div className="text-sm bg-red-50 text-red-700 rounded px-3 py-2">{error}</div>}
      {note && <div className="text-sm text-slate-500">{note}</div>}

      {phase === "done" && <div className="text-sm bg-green-50 text-green-800 rounded px-3 py-2">Checked in with the camera.</div>}

      <div className={phase === "idle" || phase === "done" ? "hidden" : "block"}>
        <video
          ref={videoRef}
          muted
          playsInline
          className={`w-full max-w-sm rounded-lg bg-slate-900 border-4 ${faceOk ? "border-green-500" : "border-slate-300"}`}
        />
      </div>

      <div className="flex gap-2">
        {(phase === "idle" || phase === "done") && (
          <button className="bg-brand text-white rounded px-4 py-1.5 text-sm" onClick={start}>
            {phase === "done" ? "Open camera again" : "Open camera"}
          </button>
        )}
        {phase === "loading" && <span className="text-sm text-slate-500">Loading camera and face model…</span>}
        {(phase === "ready" || phase === "submitting") && (
          <>
            <button
              className="bg-brand text-white rounded px-4 py-1.5 text-sm disabled:opacity-40"
              onClick={submit}
              disabled={!faceOk || phase === "submitting"}
            >
              {phase === "submitting" ? "Checking in…" : "Check in"}
            </button>
            <button
              className="text-sm text-slate-500 underline"
              onClick={() => {
                stop();
                setPhase("idle");
                setFaces(0);
              }}
            >
              Cancel
            </button>
          </>
        )}
      </div>

      <p className="text-xs text-slate-400">
        No photo is stored — only the check-in result. The server confirms your distance from the office.
      </p>
    </div>
  );
}
