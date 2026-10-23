"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  RefreshCw,
  Zap,
  VideoOff,
  FlipHorizontal,
  ThumbsUp,
  Activity,
  Sliders
} from "lucide-react";
import { analyzeImageFrame, DetectionItem } from "@/lib/api";

interface WebcamHUDProps {
  onScanComplete: (result: DetectionItem) => void;
  isAnalyzing: boolean;
  setIsAnalyzing: (analyzing: boolean) => void;
}

export const WebcamHUD: React.FC<WebcamHUDProps> = ({
  onScanComplete,
  isAnalyzing,
  setIsAnalyzing,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [streamActive, setStreamActive] = useState<boolean>(false);
  const [autoScan, setAutoScan] = useState<boolean>(false);
  const [isMirrored, setIsMirrored] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastScanTime, setLastScanTime] = useState<number>(0);
  const [currentTrigger, setCurrentTrigger] = useState<string>("web_hud");

  // High FPS Configuration State
  const [targetFps, setTargetFps] = useState<30 | 60>(60);
  const [resolution, setResolution] = useState<"720p" | "1080p">("720p");
  const [liveFps, setLiveFps] = useState<number>(0);

  // Initialize or reconfigure camera stream with target FPS & Resolution
  const startCamera = useCallback(
    async (fps: 30 | 60 = targetFps, res: "720p" | "1080p" = resolution) => {
      try {
        setErrorMessage(null);

        // Stop existing tracks cleanly if switching modes
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        const is1080 = res === "1080p";
        const constraints: MediaStreamConstraints = {
          video: {
            width: is1080 ? { ideal: 1920, min: 1280 } : { ideal: 1280, min: 640 },
            height: is1080 ? { ideal: 1080, min: 720 } : { ideal: 720, min: 480 },
            frameRate: { ideal: fps, min: fps === 60 ? 30 : 15 },
            facingMode: "user",
          },
          audio: false,
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        streamRef.current = stream;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setStreamActive(true);
        }
      } catch (err: any) {
        console.error("Camera access error with constraints:", err);
        // Fallback to basic camera if specific FPS or 1080p constraint was rejected
        try {
          const fallbackStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
          });
          streamRef.current = fallbackStream;
          if (videoRef.current) {
            videoRef.current.srcObject = fallbackStream;
            setStreamActive(true);
          }
        } catch (fallbackErr: any) {
          setErrorMessage(
            "Could not access webcam. Please ensure camera permissions are granted in your browser."
          );
          setStreamActive(false);
        }
      }
    },
    [targetFps, resolution]
  );

  useEffect(() => {
    startCamera(targetFps, resolution);

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [startCamera, targetFps, resolution]);

  // Real-Time Hardware FPS Measurement Loop
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !streamActive) return;

    let frameCount = 0;
    let lastTimestamp = performance.now();
    let callbackHandle: number | null = null;
    let animHandle: number | null = null;
    let isMounted = true;

    if ("requestVideoFrameCallback" in HTMLVideoElement.prototype) {
      const onFrame = (now: DOMHighResTimeStamp) => {
        if (!isMounted) return;
        frameCount++;
        const delta = now - lastTimestamp;
        if (delta >= 1000) {
          setLiveFps(Math.round((frameCount * 1000) / delta));
          frameCount = 0;
          lastTimestamp = now;
        }
        if (video && "requestVideoFrameCallback" in video) {
          callbackHandle = (video as any).requestVideoFrameCallback(onFrame);
        }
      };
      callbackHandle = (video as any).requestVideoFrameCallback(onFrame);
    } else {
      // Fallback frame counter for browsers without requestVideoFrameCallback
      const loop = (now: DOMHighResTimeStamp) => {
        if (!isMounted) return;
        frameCount++;
        const delta = now - lastTimestamp;
        if (delta >= 1000) {
          setLiveFps(Math.round((frameCount * 1000) / delta));
          frameCount = 0;
          lastTimestamp = now;
        }
        animHandle = requestAnimationFrame(loop);
      };
      animHandle = requestAnimationFrame(loop);
    }

    return () => {
      isMounted = false;
      if (video && callbackHandle && "cancelVideoFrameCallback" in video) {
        (video as any).cancelVideoFrameCallback(callbackHandle);
      }
      if (animHandle) {
        cancelAnimationFrame(animHandle);
      }
    };
  }, [streamActive]);

  // Capture frame as base64 JPEG
  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !streamActive) return null;

    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext("2d");
    if (!ctx) return null;

    if (isMirrored) {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.85);
  }, [streamActive, isMirrored]);

  // Execute frame analysis with backend
  const triggerScan = useCallback(
    async (source: string = "web_hud", gesture?: string) => {
      if (isAnalyzing || !streamActive) return;

      const imageB64 = captureFrame();
      if (!imageB64) return;

      try {
        setIsAnalyzing(true);
        setCurrentTrigger(source);
        setLastScanTime(Date.now());
        const result = await analyzeImageFrame(imageB64, source, gesture);
        if (result) {
          onScanComplete(result);
        }
      } catch (err: any) {
        console.error("Analysis trigger failed:", err);
        setErrorMessage(err.message || "Recognition analysis failed. Check backend connection.");
      } finally {
        setIsAnalyzing(false);
      }
    },
    [isAnalyzing, streamActive, captureFrame, onScanComplete, setIsAnalyzing]
  );

  // Auto-scan timer (8s interval to respect free tier quotas)
  useEffect(() => {
    if (!autoScan || !streamActive) return;

    const interval = setInterval(() => {
      if (!isAnalyzing && Date.now() - lastScanTime >= 8000) {
        triggerScan("auto_timer");
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [autoScan, isAnalyzing, lastScanTime, triggerScan, streamActive]);

  // Keyboard shortcut listener (SPACE for scan, A for auto-scan toggle)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault();
        triggerScan("space_key");
      } else if (e.key === "a" || e.key === "A") {
        setAutoScan((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [triggerScan]);

  // Toggle FPS target (30 -> 60 -> 30)
  const toggleFps = () => {
    const nextFps = targetFps === 60 ? 30 : 60;
    setTargetFps(nextFps);
  };

  // Toggle Resolution (720p -> 1080p -> 720p)
  const toggleResolution = () => {
    const nextRes = resolution === "720p" ? "1080p" : "720p";
    setResolution(nextRes);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Viewport Frame */}
      <div className="relative rounded-2xl overflow-hidden glass-panel-glow border-2 border-cyan-500/30 aspect-[16/10] bg-slate-950 flex items-center justify-center shadow-2xl">
        {/* Video Feed with GPU Acceleration */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`w-full h-full object-cover transition-transform duration-200 transform-gpu will-change-transform ${
            isMirrored ? "-scale-x-100" : ""
          } ${!streamActive ? "hidden" : "block"}`}
        />

        {/* Video Inactive Fallback */}
        {!streamActive && (
          <div className="flex flex-col items-center justify-center p-6 text-center text-slate-400">
            <VideoOff className="w-12 h-12 text-slate-600 mb-3" />
            <p className="text-sm font-medium">{errorMessage || "Webcam is not streaming."}</p>
            <button
              onClick={() => startCamera(targetFps, resolution)}
              className="mt-4 px-4 py-2 text-xs font-mono rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition-all"
            >
              Retry Camera Connection
            </button>
          </div>
        )}

        {/* HUD Visual Overlay Elements */}
        {streamActive && (
          <>
            {/* Top HUD Status Bar with Live Measured FPS */}
            <div className="absolute top-0 left-0 right-0 p-3.5 bg-gradient-to-b from-black/80 via-black/40 to-transparent flex items-center justify-between text-xs font-mono text-cyan-300 pointer-events-none">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                <span className="font-bold tracking-wider">
                  LIVE FEED [{resolution.toUpperCase()}]
                </span>
              </div>
              <div className="flex items-center gap-2.5">
                {/* Live Real-Time Hardware FPS Badge */}
                <span
                  className={`px-2.5 py-0.5 rounded-full border text-[11px] font-bold flex items-center gap-1.5 transition-all shadow-sm ${
                    liveFps >= 50
                      ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.3)]"
                      : liveFps >= 25
                      ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-300"
                      : "bg-amber-500/20 border-amber-500/40 text-amber-300"
                  }`}
                  title="Measured real-time camera hardware FPS"
                >
                  <Activity className="w-3 h-3 animate-pulse" />
                  <span>FPS: {liveFps > 0 ? liveFps : targetFps}</span>
                  <span className="text-[9px] opacity-70">({targetFps} max)</span>
                </span>

                <span
                  className={`px-2 py-0.5 rounded border text-[11px] ${
                    autoScan
                      ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                      : "bg-slate-800/80 border-slate-700 text-slate-400"
                  }`}
                >
                  Auto-Scan: {autoScan ? "ACTIVE (8s)" : "OFF"}
                </span>
              </div>
            </div>

            {/* Corner Targeting Brackets */}
            <div className="absolute inset-4 pointer-events-none border border-cyan-500/20 rounded-xl">
              <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-cyan-400 rounded-tl-lg" />
              <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-cyan-400 rounded-tr-lg" />
              <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-cyan-400 rounded-bl-lg" />
              <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-cyan-400 rounded-br-lg" />
            </div>

            {/* Center Reticle */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-20 h-20 border border-cyan-400/30 rounded-full flex items-center justify-center">
                <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full" />
              </div>
            </div>

            {/* Analyzing Scanner Animation */}
            {isAnalyzing && (
              <div className="absolute inset-0 bg-cyan-950/50 backdrop-blur-[2px] flex flex-col items-center justify-center z-20 pointer-events-none">
                <div className="w-24 h-24 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mb-4" />
                <p className="font-mono text-sm font-semibold tracking-wider text-cyan-300 animate-pulse uppercase">
                  Multi-Agent Vision, Voice & Commerce Pipeline...
                </p>
                <p className="font-mono text-xs text-slate-400 mt-1">
                  Gemini 3.5 Flash Lite • Edge TTS • MongoDB Atlas
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Control Actions Bar */}
      <div className="glass-panel rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3">
        {/* Main Trigger Button */}
        <button
          onClick={() => triggerScan("web_hud")}
          disabled={isAnalyzing || !streamActive}
          className="flex-1 min-w-[180px] flex items-center justify-center gap-2.5 px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 via-sky-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 active:scale-[0.98] text-white font-semibold text-sm tracking-wide shadow-[0_0_20px_rgba(6,182,212,0.4)] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isAnalyzing ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Analyzing Pipeline...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Scan Frame (SPACE)</span>
            </>
          )}
        </button>

        {/* Thumbs-Up Gesture Trigger Button */}
        <button
          onClick={() => triggerScan("gesture_thumbs_up", "thumbs_up")}
          disabled={isAnalyzing || !streamActive}
          className="flex items-center gap-2 px-3.5 py-3 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 font-mono text-xs transition-all active:scale-95 disabled:opacity-50"
          title="Trigger analysis simulating thumbs-up gesture"
        >
          <ThumbsUp className="w-4 h-4" />
          <span>Thumbs-Up 👍</span>
        </button>

        {/* Auto-Scan Toggle Button */}
        <button
          onClick={() => setAutoScan((prev) => !prev)}
          className={`flex items-center gap-2 px-3.5 py-3 rounded-xl font-mono text-xs border transition-all ${
            autoScan
              ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.3)]"
              : "bg-slate-800/80 hover:bg-slate-700/80 border-slate-700 text-slate-300"
          }`}
          title="Toggle Auto-Scan every 8 seconds (Shortcut: A)"
        >
          <Zap className={`w-4 h-4 ${autoScan ? "text-emerald-400 fill-emerald-400" : ""}`} />
          <span>Auto: {autoScan ? "ON" : "OFF"}</span>
        </button>

        {/* FPS Mode Switcher Button (30 FPS / 60 FPS) */}
        <button
          onClick={toggleFps}
          className={`flex items-center gap-1.5 px-3 py-3 rounded-xl font-mono text-xs border transition-all active:scale-95 ${
            targetFps === 60
              ? "bg-indigo-500/20 border-indigo-500/50 text-indigo-300 shadow-[0_0_15px_rgba(99,102,241,0.3)]"
              : "bg-slate-800/80 hover:bg-slate-700/80 border-slate-700 text-slate-300"
          }`}
          title="Click to toggle camera frame rate (60 FPS Ultra Smooth / 30 FPS Standard)"
        >
          <Zap className={`w-3.5 h-3.5 ${targetFps === 60 ? "text-indigo-400 fill-indigo-400" : ""}`} />
          <span>{targetFps === 60 ? "60 FPS ⚡" : "30 FPS"}</span>
        </button>

        {/* Resolution Switcher (720p / 1080p) */}
        <button
          onClick={toggleResolution}
          className="px-2.5 py-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 hover:text-cyan-400 font-mono text-xs transition-all active:scale-95"
          title="Click to toggle resolution between 720p (High-FPS Recommended) and 1080p (Full HD)"
        >
          {resolution.toUpperCase()}
        </button>

        {/* Mirror Toggle Button */}
        <button
          onClick={() => setIsMirrored((prev) => !prev)}
          className="p-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 hover:text-cyan-400 transition-all active:scale-95"
          title="Toggle Mirror View"
        >
          <FlipHorizontal className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
