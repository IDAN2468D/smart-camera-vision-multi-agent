"use client";

import React, { useState } from "react";
import { DetectionItem, getExportUrl } from "@/lib/api";
import {
  Search,
  Database,
  ChevronRight,
  Clock,
  User,
  Hand,
  FileSpreadsheet,
  FileText,
  X,
  Maximize2,
  Tag,
  Sparkles
} from "lucide-react";

interface DetectionHistoryProps {
  detections: DetectionItem[];
  onSelectDetection: (item: DetectionItem) => void;
  onSearch: (query: string, mode: "semantic" | "keyword") => void;
  activeItem?: DetectionItem | null;
}

export const DetectionHistory: React.FC<DetectionHistoryProps> = ({
  detections,
  onSelectDetection,
  onSearch,
  activeItem,
}) => {
  const [query, setQuery] = useState("");
  const [searchMode, setSearchMode] = useState<"semantic" | "keyword">("semantic");
  const [lightboxItem, setLightboxItem] = useState<DetectionItem | null>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    onSearch(val, searchMode);
  };

  const handleModeSwitch = (newMode: "semantic" | "keyword") => {
    setSearchMode(newMode);
    if (query) {
      onSearch(query, newMode);
    }
  };

  const handleExport = (format: "excel" | "pdf") => {
    const url = getExportUrl(format, 100);
    window.open(url, "_blank");
  };

  return (
    <>
      <div className="glass-panel rounded-2xl p-4 flex flex-col gap-3.5 border border-cyan-500/20 max-h-[600px]">
        {/* Header with Export Controls */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold font-mono tracking-wider uppercase text-slate-200">
              Atlas Log ({detections.length})
            </h3>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handleExport("excel")}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-500/30 text-emerald-300 text-[11px] font-mono transition-all"
              title="ייצא לאקסל (.xlsx)"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Excel</span>
            </button>
            <button
              onClick={() => handleExport("pdf")}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-950/60 hover:bg-rose-900/60 border border-rose-500/30 text-rose-300 text-[11px] font-mono transition-all"
              title="ייצא לדוח PDF"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>PDF</span>
            </button>
          </div>
        </div>

        {/* Search Mode Selector & Input Box */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span className="flex items-center gap-1 text-slate-300">
              <Sparkles className="w-3 h-3 text-emerald-400" />
              <span>Search Engine</span>
            </span>
            <div className="inline-flex rounded-lg bg-slate-900/90 p-0.5 border border-slate-800">
              <button
                type="button"
                onClick={() => handleModeSwitch("semantic")}
                className={`px-2 py-0.5 rounded-md text-[10px] font-mono transition-all flex items-center gap-1 ${
                  searchMode === "semantic"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="Atlas Vector Search מול וקטורי Gemini (Visual RAG)"
              >
                <Sparkles className="w-2.5 h-2.5" />
                <span>Visual RAG</span>
              </button>
              <button
                type="button"
                onClick={() => handleModeSwitch("keyword")}
                className={`px-2 py-0.5 rounded-md text-[10px] font-mono transition-all flex items-center gap-1 ${
                  searchMode === "keyword"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="סינון לפי שם אובייקט מדויק"
              >
                <Search className="w-2.5 h-2.5" />
                <span>Exact Name</span>
              </button>
            </div>
          </div>

          <div className="relative">
            {searchMode === "semantic" ? (
              <Sparkles className="w-4 h-4 text-emerald-400 absolute left-3 top-1/2 -translate-y-1/2" />
            ) : (
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            )}
            <input
              type="text"
              value={query}
              onChange={handleSearchChange}
              placeholder={
                searchMode === "semantic"
                  ? "Visual RAG (e.g. coffee cup, device with screen, something blue)..."
                  : "Filter by object name (e.g. Smartphone, Face)..."
              }
              className={`w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900/80 border text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none transition-all font-mono ${
                searchMode === "semantic"
                  ? "border-emerald-500/40 focus:border-emerald-400"
                  : "border-slate-700/80 focus:border-cyan-400"
              }`}
            />
          </div>
        </div>

        {/* Detections List with WebP Thumbnails */}
        <div className="overflow-y-auto space-y-2 pr-1 flex-1">
          {detections.length === 0 ? (
            <div className="text-center py-10 text-xs font-mono text-slate-500">
              No detection records match your query.
            </div>
          ) : (
            detections.map((item, idx) => {
              const isSelected = activeItem?.timestamp === item.timestamp;
              return (
                <div
                  key={idx}
                  onClick={() => onSelectDetection(item)}
                  className={`p-2.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between gap-3 text-left ${
                    isSelected
                      ? "bg-cyan-950/40 border-cyan-500/60 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                      : "bg-slate-900/50 hover:bg-slate-800/60 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {/* WebP Thumbnail with Lightbox click */}
                  {item.thumbnail_base64 ? (
                    <div
                      className="relative w-14 h-11 rounded-lg overflow-hidden border border-slate-700/80 flex-shrink-0 group"
                      onClick={(e) => {
                        e.stopPropagation();
                        setLightboxItem(item);
                      }}
                      title="לחץ להגדלת תמונה"
                    >
                      <img
                        src={item.thumbnail_base64}
                        alt={item.object_name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                        <Maximize2 className="w-3.5 h-3.5 text-cyan-300" />
                      </div>
                    </div>
                  ) : (
                    <div className="w-14 h-11 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center justify-center flex-shrink-0">
                      <Tag className="w-4 h-4 text-slate-500" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-xs font-bold text-slate-100 truncate">
                        {item.object_name}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {item.category}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>

                      <span className="text-cyan-400 font-semibold">
                        {Math.round(item.confidence * 100)}%
                      </span>

                      {typeof item.similarity_score === "number" && (
                        <span
                          className="flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-500/40 font-bold"
                          title={`Visual RAG similarity score (${item.embedding_model || "gemini-embedding-2"})`}
                        >
                          <Sparkles className="w-2.5 h-2.5 text-emerald-400" />
                          {Math.round(item.similarity_score * 100)}% Match
                        </span>
                      )}

                      {item.face_detected && (
                        <span className="flex items-center text-emerald-400 text-[10px]" title="Face Detected">
                          <User className="w-2.5 h-2.5 mr-0.5" /> Face
                        </span>
                      )}

                      {item.hands_detected && (
                        <span className="flex items-center text-amber-400 text-[10px]" title="Hands Detected">
                          <Hand className="w-2.5 h-2.5 mr-0.5" /> Hands
                        </span>
                      )}
                    </div>
                  </div>

                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 flex-shrink-0" />
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Lightbox Modal for Snapshot Inspection */}
      {lightboxItem && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setLightboxItem(null)}
        >
          <div
            className="glass-panel-glow max-w-lg w-full rounded-2xl p-5 border border-cyan-500/40 bg-slate-950 flex flex-col gap-4 relative animate-in fade-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">{lightboxItem.object_name}</h3>
                <p className="text-xs text-slate-400 font-mono">
                  {lightboxItem.category} | {new Date(lightboxItem.timestamp).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => setLightboxItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {lightboxItem.thumbnail_base64 && (
              <div className="rounded-xl overflow-hidden border border-slate-800 bg-black aspect-video flex items-center justify-center">
                <img
                  src={lightboxItem.thumbnail_base64}
                  alt={lightboxItem.object_name}
                  className="w-full h-full object-contain"
                />
              </div>
            )}

            <div className="text-xs text-slate-300 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
              <span className="text-[10px] uppercase font-mono text-cyan-400 block mb-1">Visual Details:</span>
              <p>{lightboxItem.visual_description}</p>
            </div>

            {lightboxItem.product_info && (
              <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-xs">
                <div className="flex justify-between items-center text-emerald-300 font-bold mb-1">
                  <span>{lightboxItem.product_info.model_name}</span>
                  <span>{lightboxItem.product_info.estimated_price_ils}</span>
                </div>
                {lightboxItem.product_info.specs_summary && (
                  <p dir="rtl" className="text-slate-300 text-right">{lightboxItem.product_info.specs_summary}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};
