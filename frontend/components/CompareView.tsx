"use client";

import React, { useState } from "react";
import { compareProducts, CompareAnalysisResult } from "../lib/api";

interface CompareViewProps {
  isOpen: boolean;
  onClose: () => void;
  currentFrameBase64?: string | null;
}

export default function CompareView({
  isOpen,
  onClose,
  currentFrameBase64,
}: CompareViewProps) {
  const [labelA, setLabelA] = useState("");
  const [labelB, setLabelB] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareAnalysisResult | null>(null);

  if (!isOpen) return null;

  const handleRunCompare = async () => {
    if (!currentFrameBase64 && !labelA.trim() && !labelB.trim()) {
      alert("נא להזין שמות מוצרים להשוואה או ללכוד פריים.");
      return;
    }
    setLoading(true);
    try {
      const data = await compareProducts(
        currentFrameBase64 || "",
        undefined,
        labelA || "מוצר א'",
        labelB || "מוצר ב'"
      );
      setResult(data);
    } catch (err: any) {
      console.error("Comparison error:", err);
      alert(err.message || "שגיאה בביצוע השוואת מוצרים");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fadeIn">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚖️</span>
            <h2 className="text-lg font-bold text-slate-100">
              סטודיו להשוואת מוצרים (Compare Studio v3)
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 text-xl font-bold p-1 rounded-lg"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-cyan-400 mb-1">
                מוצר א' (Item A):
              </label>
              <input
                type="text"
                value={labelA}
                onChange={(e) => setLabelA(e.target.value)}
                placeholder="למשל: iPhone 15 Pro"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-400"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-purple-400 mb-1">
                מוצר ב' (Item B):
              </label>
              <input
                type="text"
                value={labelB}
                onChange={(e) => setLabelB(e.target.value)}
                placeholder="למשל: Galaxy S24 Ultra"
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-purple-400"
              />
            </div>
          </div>

          <button
            onClick={handleRunCompare}
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-indigo-500 to-purple-600 text-white font-semibold text-sm hover:opacity-90 disabled:opacity-40 transition shadow"
          >
            {loading ? "מבצע סריקה והשוואה..." : "השווה מוצרים והצג המלצה (₪)"}
          </button>

          {/* Results Table */}
          {result && (
            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800/60 p-3 rounded-xl border border-cyan-500/30 text-center">
                  <div className="text-xs text-slate-400">{result.item_a_name}</div>
                  <div className="text-lg font-bold text-cyan-400">
                    {result.price_a_ils || "מחיר לא זמין"}
                  </div>
                </div>
                <div className="bg-slate-800/60 p-3 rounded-xl border border-purple-500/30 text-center">
                  <div className="text-xs text-slate-400">{result.item_b_name}</div>
                  <div className="text-lg font-bold text-purple-400">
                    {result.price_b_ils || "מחיר לא זמין"}
                  </div>
                </div>
              </div>

              {result.comparison_points && result.comparison_points.length > 0 && (
                <div className="border border-slate-800 rounded-xl overflow-hidden">
                  <table className="w-full text-xs text-right text-slate-200">
                    <thead className="bg-slate-800 text-slate-400 uppercase">
                      <tr>
                        <th className="p-2.5">מאפיין</th>
                        <th className="p-2.5">{result.item_a_name}</th>
                        <th className="p-2.5">{result.item_b_name}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {result.comparison_points.map((pt, i) => (
                        <tr key={i} className="hover:bg-slate-800/40">
                          <td className="p-2.5 font-semibold text-slate-300">{pt.feature}</td>
                          <td className="p-2.5 text-slate-300">{pt.item_a}</td>
                          <td className="p-2.5 text-slate-300">{pt.item_b}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {result.winner_recommendation_hebrew && (
                <div className="p-3 bg-gradient-to-r from-emerald-950/40 to-slate-900 border border-emerald-500/40 rounded-xl">
                  <div className="text-xs font-bold text-emerald-400 mb-1">
                    🏆 המלצת רכישה (AI Synthesis):
                  </div>
                  <div className="text-sm text-slate-200">
                    {result.winner_recommendation_hebrew}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
