"use client";

import React, { useState } from "react";
import { askVisionLive, AskVisionResponse } from "../lib/api";
import { spatialAudio } from "../lib/spatialAudio";

interface VoiceQuestionBarProps {
  onCaptureFrame: () => string | null;
  isProcessing?: boolean;
}

export default function VoiceQuestionBar({
  onCaptureFrame,
  isProcessing = false,
}: VoiceQuestionBarProps) {
  const [question, setQuestion] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [loading, setLoading] = useState(false);
  const [lastResponse, setLastResponse] = useState<AskVisionResponse | null>(null);

  const startVoiceInput = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("דפדפן זה אינו תומך בזיהוי דיבור ישיר. ניתן להקליד את השאלה בתיבה.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "he-IL";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setQuestion(transcript);
      handleAsk(transcript);
    };

    recognition.start();
  };

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || question).trim();
    if (!q) return;

    const frameB64 = onCaptureFrame();
    if (!frameB64) {
      alert("לא ניתן ללכוד פריים מהמצלמה כרגע.");
      return;
    }

    setLoading(true);
    try {
      const res = await askVisionLive(frameB64, q);
      setLastResponse(res);
      if (res.tts_audio_base64) {
        spatialAudio.playSpatialSpeech(res.tts_audio_base64, res.pan_x || 0);
      }
    } catch (err: any) {
      console.error("Ask Vision error:", err);
      alert(err.message || "שגיאה בביצוע שאלת Vision Live");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full bg-slate-900/90 backdrop-blur-md border border-cyan-500/30 rounded-2xl p-3 shadow-xl">
      <div className="flex items-center gap-2">
        <button
          onClick={startVoiceInput}
          disabled={loading || isProcessing || isListening}
          className={`p-2.5 rounded-xl transition flex items-center justify-center ${
            isListening
              ? "bg-rose-600 text-white animate-pulse"
              : "bg-cyan-600/20 text-cyan-400 hover:bg-cyan-600/30 border border-cyan-500/30"
          }`}
          title="שאל בדיבור קולי (עברית)"
        >
          {isListening ? (
            <span className="text-sm font-bold animate-ping">🎙️ מאזין...</span>
          ) : (
            <span className="text-lg">🎙️</span>
          )}
        </button>

        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="שאל את ה-Vision Live על מה שאתה רואה במצלמה... (למשל: מה רשום על הכוס?)"
          disabled={loading || isProcessing}
          className="flex-1 bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-cyan-400"
        />

        <button
          onClick={() => handleAsk()}
          disabled={loading || !question.trim() || isProcessing}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium text-sm hover:opacity-90 disabled:opacity-40 transition shadow"
        >
          {loading ? "מעבד..." : "שאל Vision"}
        </button>
      </div>

      {lastResponse && (
        <div className="mt-3 p-3 bg-slate-800/70 border border-cyan-500/20 rounded-xl flex items-start justify-between gap-3 animate-fadeIn">
          <div>
            <div className="text-xs text-cyan-400 font-semibold mb-1">
              תשובה קולית מסונכרנת (Live Vision):
            </div>
            <div className="text-sm text-slate-200">{lastResponse.answer_hebrew}</div>
          </div>
          {lastResponse.tts_audio_base64 && (
            <button
              onClick={() =>
                spatialAudio.playSpatialSpeech(
                  lastResponse.tts_audio_base64!,
                  lastResponse.pan_x || 0
                )
              }
              className="text-xs text-cyan-300 hover:text-cyan-100 bg-cyan-950/60 border border-cyan-500/30 px-2 py-1 rounded-lg shrink-0 flex items-center gap-1"
            >
              <span>🔊</span> שמע שוב
            </button>
          )}
        </div>
      )}
    </div>
  );
}
