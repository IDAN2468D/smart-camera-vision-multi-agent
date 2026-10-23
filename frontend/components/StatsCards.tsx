"use client";

import React from "react";
import { DetectionItem, TelemetryMetrics } from "@/lib/api";
import { Database, UserCheck, Layers, Cpu, Coins, ShieldCheck } from "lucide-react";

interface StatsCardsProps {
  detections: DetectionItem[];
  modelId?: string;
  telemetry?: TelemetryMetrics;
}

export const StatsCards: React.FC<StatsCardsProps> = ({ detections, modelId, telemetry }) => {
  const totalScans = detections.length;
  const categories = new Set(detections.map((d) => d.category)).size;
  const humanDetections = detections.filter((d) => d.face_detected || d.hands_detected).length;
  const humanEvaluated = detections.filter((d) => d.human_evaluated).length;

  const stats = [
    {
      label: "Atlas Records",
      value: totalScans,
      icon: Database,
      accent: "text-cyan-400 border-cyan-500/30 bg-cyan-500/10",
    },
    {
      label: "Face/Hand Detections",
      value: humanDetections,
      icon: UserCheck,
      accent: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
    },
    {
      label: "HITL Evaluated",
      value: humanEvaluated > 0 ? `${humanEvaluated} verified` : "Active",
      icon: ShieldCheck,
      accent: "text-purple-400 border-purple-500/30 bg-purple-500/10",
      isText: true,
    },
    {
      label: "Avg Cost / Scan",
      value: telemetry?.cost_per_scan_ils ? `${telemetry.cost_per_scan_ils}` : "₪0.0012",
      icon: Coins,
      accent: "text-amber-400 border-amber-500/30 bg-amber-500/10",
      isText: true,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {stats.map((stat, idx) => {
        const Icon = stat.icon;
        return (
          <div
            key={idx}
            className="glass-panel rounded-xl p-3.5 border flex items-center justify-between gap-3 shadow-sm hover:border-cyan-500/40 transition-all"
          >
            <div>
              <p className="text-[11px] font-mono uppercase text-slate-400">{stat.label}</p>
              <p
                className={`text-lg font-bold tracking-tight mt-0.5 ${
                  stat.isText ? "text-sm font-mono text-slate-200 truncate max-w-[130px]" : "text-white"
                }`}
              >
                {stat.value}
              </p>
            </div>
            <div className={`p-2.5 rounded-xl border ${stat.accent}`}>
              <Icon className="w-4 h-4" />
            </div>
          </div>
        );
      })}
    </div>
  );
};
