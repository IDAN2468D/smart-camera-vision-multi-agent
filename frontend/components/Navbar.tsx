"use client";

import React from "react";
import { HealthResponse } from "@/lib/api";
import { Eye, Database, Cpu, Activity, RefreshCw, Sparkles } from "lucide-react";

interface NavbarProps {
  health: HealthResponse | null;
  onRefresh: () => void;
  isLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ health, onRefresh, isLoading }) => {
  const isOnline = health?.status === "online";
  const dbConnected = health?.database === "connected";

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-cyan-500/20 px-4 lg:px-8 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
            <Eye className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-wider uppercase text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400">
                Vision Multi-Agent HUD
              </h1>
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                Live AI
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">Agno • Gemini Vision • MongoDB Atlas</p>
          </div>
        </div>

        {/* Status Indicators */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs font-mono">
          {/* Backend Status */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all ${
              isOnline
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-rose-500/10 border-rose-500/30 text-rose-400"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>API: {isOnline ? "ONLINE (5000)" : "OFFLINE"}</span>
            <span
              className={`w-2 h-2 rounded-full ${
                isOnline ? "bg-emerald-400 animate-ping" : "bg-rose-500"
              }`}
            />
          </div>

          {/* Database Status */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all ${
              dbConnected
                ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
                : "bg-amber-500/10 border-amber-500/30 text-amber-300"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Atlas DB: {dbConnected ? "CONNECTED" : "DISCONNECTED"}</span>
          </div>

          {/* Active Model */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-indigo-500/10 border-indigo-500/30 text-indigo-300">
            <Cpu className="w-3.5 h-3.5" />
            <span>Model: {health?.model_id || "gemini-3.5-flash-lite"}</span>
          </div>

          {/* MCP Protocol Badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border bg-purple-500/10 border-purple-500/30 text-purple-300 text-xs font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
            <span>MCP: 5006</span>
          </div>

          {/* Visual RAG Embedding Microservice Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border bg-emerald-500/10 border-emerald-500/30 text-emerald-300 text-xs font-mono">
            <Sparkles className="w-3 h-3 text-emerald-400 animate-pulse" />
            <span>RAG: 5008</span>
          </div>

          {/* Swagger OpenAPI Docs Link */}
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-cyan-400 transition-all text-xs font-mono"
            title="Open Interactive Swagger / OpenAPI Documentation"
          >
            <span>API Docs</span>
          </a>

          {/* Refresh Action */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 hover:text-cyan-400 transition-all active:scale-95 disabled:opacity-50"
            title="Refresh System Data"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
