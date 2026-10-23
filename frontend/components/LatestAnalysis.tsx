"use client";

import React, { useRef, useState, useEffect } from "react";
import { DetectionItem, submitHumanFeedback } from "@/lib/api";
import {
  User,
  Hand,
  Tag,
  FileText,
  Sparkles,
  Clock,
  Volume2,
  VolumeX,
  Play,
  Pause,
  ShoppingBag,
  Zap,
  ThumbsUp,
  ThumbsDown,
  ShieldCheck,
  CheckCircle,
  Cpu
} from "lucide-react";

interface LatestAnalysisProps {
  detection: DetectionItem | null;
}

export const LatestAnalysis: React.FC<LatestAnalysisProps> = ({ detection }) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [feedbackSent, setFeedbackSent] = useState<"verified" | "rejected" | null>(null);

  // Reset feedback state on new detection
  useEffect(() => {
    setFeedbackSent(null);
  }, [detection?.timestamp]);

  // Auto-play Hebrew voice when a new detection arrives (if not muted)
  useEffect(() => {
    if (detection?.tts_audio_base64 && audioRef.current && !isMuted) {
      audioRef.current.src = detection.tts_audio_base64;
      audioRef.current.currentTime = 0;
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((e) => {
          console.debug("Audio autoplay prevented by browser:", e);
          setIsPlaying(false);
        });
    }
  }, [detection?.timestamp, isMuted]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  };

  const handleFeedback = async (isAccurate: boolean) => {
    if (!detection) return;
    setFeedbackSent(isAccurate ? "verified" : "rejected");
    await submitHumanFeedback(detection.timestamp, isAccurate);
  };

  if (!detection) {
    return (
      <div className="glass-panel rounded-2xl p-6 text-center flex flex-col items-center justify-center min-h-[420px] border border-cyan-500/20">
        <div className="p-4 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 mb-4 animate-bounce">
          <Sparkles className="w-8 h-8" />
        </div>
        <h3 className="text-base font-semibold text-slate-200 uppercase tracking-wider font-mono">
          Ready for Live Analysis
        </h3>
        <p className="text-xs text-slate-400 max-w-sm mt-2 leading-relaxed">
          Point your camera at a face, hand gesture, or physical object and press{" "}
          <kbd className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-300 font-mono text-[11px]">
            SPACE
          </kbd>{" "}
          or show <span className="text-amber-400 font-bold">Thumbs-Up 👍</span> to trigger multi-agent recognition.
        </p>
      </div>
    );
  }

  const confidencePct = Math.round(detection.confidence * 100);

  return (
    <div className="glass-panel-glow rounded-2xl p-5 border border-cyan-500/30 flex flex-col gap-4 shadow-xl">
      {/* Hidden audio element for Hebrew speech */}
      <audio
        ref={audioRef}
        onEnded={() => setIsPlaying(false)}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
      />

      {/* Header Banner */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-3.5">
        <div className="flex items-center gap-3">
          {detection.thumbnail_base64 && (
            <img
              src={detection.thumbnail_base64}
              alt={detection.object_name}
              className="w-16 h-12 object-cover rounded-lg border border-cyan-500/30 shadow-md"
            />
          )}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                {detection.category}
              </span>
              {detection.trigger_source && (
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                  {detection.trigger_source.includes("gesture") ? (
                    <ThumbsUp className="w-2.5 h-2.5" />
                  ) : (
                    <Zap className="w-2.5 h-2.5" />
                  )}
                  {detection.trigger_source}
                </span>
              )}
              <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(detection.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <h2 className="text-xl font-bold text-white mt-1 tracking-wide">
              {detection.object_name}
            </h2>
          </div>
        </div>

        {/* Confidence Progress Meter */}
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-1.5 text-xs font-mono">
            <span className="text-slate-400">Confidence:</span>
            <span className="text-cyan-400 font-bold">{confidencePct}%</span>
          </div>
          <div className="w-24 h-2 bg-slate-800 rounded-full mt-1.5 overflow-hidden border border-slate-700">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full transition-all duration-500"
              style={{ width: `${confidencePct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Hebrew Voice Agent (TTS) Audio Bar */}
      {detection.tts_audio_base64 && (
        <div className="p-2.5 px-3 rounded-xl bg-cyan-950/40 border border-cyan-500/40 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <button
              onClick={togglePlay}
              className="w-8 h-8 rounded-full bg-cyan-500 hover:bg-cyan-400 text-slate-950 flex items-center justify-center transition-all shadow-md active:scale-95"
              title={isPlaying ? "השהה קריינות" : "השמע קריינות בעברית"}
            >
              {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
            </button>
            <div className="flex flex-col">
              <span className="text-xs font-semibold text-cyan-200 font-sans flex items-center gap-1.5">
                <span>קריינות AI בעברית (Voice Agent)</span>
                {isPlaying && (
                  <span className="flex items-center gap-0.5 h-3">
                    <span className="w-1 bg-cyan-400 animate-[bounce_0.6s_infinite_100ms] h-full rounded" />
                    <span className="w-1 bg-cyan-400 animate-[bounce_0.6s_infinite_200ms] h-2 rounded" />
                    <span className="w-1 bg-cyan-400 animate-[bounce_0.6s_infinite_300ms] h-full rounded" />
                  </span>
                )}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Edge Neural Voice (Avri)</span>
            </div>
          </div>

          <button
            onClick={() => {
              if (isPlaying) {
                audioRef.current?.pause();
                setIsPlaying(false);
              }
              setIsMuted((prev) => !prev);
            }}
            className="p-1.5 rounded-lg text-slate-400 hover:text-cyan-300 transition-colors"
            title={isMuted ? "בטל השתקה אוטומטית" : "השתק אוטומטית"}
          >
            {isMuted ? <VolumeX className="w-4 h-4 text-red-400" /> : <Volume2 className="w-4 h-4 text-cyan-400" />}
          </button>
        </div>
      )}

      {/* Feature Badges Grid (Face, Hands, Guardrails) */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Face Status */}
        <div
          className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-mono ${
            detection.face_detected
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-slate-900/60 border-slate-800 text-slate-500"
          }`}
        >
          <User className="w-4 h-4" />
          <span>Face: {detection.face_detected ? "DETECTED ✅" : "NONE"}</span>
        </div>

        {/* Hands Status */}
        <div
          className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-mono ${
            detection.hands_detected
              ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
              : "bg-slate-900/60 border-slate-800 text-slate-500"
          }`}
        >
          <Hand className="w-4 h-4" />
          <span>Hands: {detection.hands_detected ? "DETECTED ✋" : "NONE"}</span>
        </div>
      </div>

      {/* AI Guardrails & Safety Badge */}
      <div className="flex items-center justify-between px-3 py-2 rounded-xl bg-slate-900/70 border border-slate-800 text-[11px] font-mono">
        <div className="flex items-center gap-2 text-emerald-400">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Guardrails: PII Redacted & Safe</span>
        </div>
        <div className="flex items-center gap-1.5 text-slate-400">
          <Cpu className="w-3 h-3 text-cyan-400" />
          <span>Tokens: ~630 • Cost: ~₪0.001</span>
        </div>
      </div>

      {/* Commerce & Price Intelligence Card */}
      {detection.product_info && (
        <div className="p-3.5 rounded-xl bg-gradient-to-r from-emerald-950/40 to-slate-900/70 border border-emerald-500/40 text-xs">
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="font-semibold text-emerald-400 flex items-center gap-1.5 font-mono uppercase text-[11px]">
              <ShoppingBag className="w-3.5 h-3.5" />
              Commerce & Price Intelligence
            </span>
            {detection.product_info.estimated_price_ils && (
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 font-mono text-xs">
                {detection.product_info.estimated_price_ils}
              </span>
            )}
          </div>
          <div className="text-white font-medium mb-1">
            {detection.product_info.model_name}
          </div>
          {detection.product_info.specs_summary && (
            <p dir="rtl" className="text-slate-300 text-right font-sans text-xs mt-1 leading-relaxed">
              {detection.product_info.specs_summary}
            </p>
          )}
        </div>
      )}

      {/* Detected Entities Chips */}
      {detection.detected_entities && detection.detected_entities.length > 0 && (
        <div>
          <span className="text-[11px] font-mono uppercase text-slate-400 flex items-center gap-1 mb-1.5">
            <Tag className="w-3 h-3 text-cyan-400" />
            Identified Elements:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {detection.detected_entities.map((item, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-lg text-xs font-mono bg-slate-800/80 border border-slate-700 text-slate-200"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* OCR Detected Text */}
      {detection.detected_text && (
        <div className="p-3 rounded-xl bg-slate-900/70 border border-cyan-500/20 text-xs font-mono">
          <div className="flex items-center gap-1.5 text-cyan-400 text-[11px] uppercase mb-1 font-semibold">
            <FileText className="w-3.5 h-3.5" />
            <span>Extracted OCR Text:</span>
          </div>
          <p className="text-slate-300 bg-slate-950/60 p-2 rounded border border-slate-800/80 leading-relaxed">
            "{detection.detected_text}"
          </p>
        </div>
      )}

      {/* Visual Description */}
      <div>
        <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
          Visual Description:
        </span>
        <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/60">
          {detection.visual_description}
        </p>
      </div>

      {/* AI Hebrew Enrichment Summary Card */}
      <div
        dir="rtl"
        className="p-3.5 rounded-xl bg-gradient-to-br from-indigo-950/40 via-slate-900/80 to-cyan-950/40 border border-indigo-500/30 text-right shadow-md"
      >
        <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-xs">
          <Sparkles className="w-4 h-4 animate-spin text-cyan-400" />
          <span>תובנות סוכן הידע וההיסטוריה (Knowledge Agent):</span>
        </div>
        <p className="text-xs text-slate-200 leading-relaxed font-sans font-medium">
          {detection.enrichment_summary}
        </p>
      </div>

      {/* Human-In-The-Loop (HITL) Evaluation Widget */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-cyan-500/20 flex items-center justify-between gap-2 text-xs">
        <span className="font-sans text-slate-300">האם זיהוי ה-AI היה מדויק? (HITL)</span>
        {feedbackSent ? (
          <span className="flex items-center gap-1 text-emerald-400 font-mono text-xs">
            <CheckCircle className="w-3.5 h-3.5" />
            {feedbackSent === "verified" ? "אומת בהצלחה ✅" : "סומן לבדיקה ⚠️"}
          </span>
        ) : (
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handleFeedback(true)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-950/60 hover:bg-emerald-800/60 border border-emerald-500/40 text-emerald-300 font-mono text-[11px] transition-all active:scale-95"
            >
              <ThumbsUp className="w-3 h-3" />
              <span>מדויק</span>
            </button>
            <button
              onClick={() => handleFeedback(false)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-950/60 hover:bg-rose-800/60 border border-rose-500/40 text-rose-300 font-mono text-[11px] transition-all active:scale-95"
            >
              <ThumbsDown className="w-3 h-3" />
              <span>תיקון</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
