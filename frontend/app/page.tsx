"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  getSystemHealth,
  fetchRecentDetections,
  searchDetections,
  DetectionItem,
  HealthResponse,
} from "@/lib/api";
import { Navbar } from "@/components/Navbar";
import { StatsCards } from "@/components/StatsCards";
import { WebcamHUD } from "@/components/WebcamHUD";
import { LatestAnalysis } from "@/components/LatestAnalysis";
import { DetectionHistory } from "@/components/DetectionHistory";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [detections, setDetections] = useState<DetectionItem[]>([]);
  const [activeDetection, setActiveDetection] = useState<DetectionItem | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [sseConnected, setSseConnected] = useState<boolean>(false);

  // Load initial health & detections
  const loadData = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const [healthData, detectionsData] = await Promise.all([
        getSystemHealth(),
        fetchRecentDetections(30),
      ]);

      setHealth(healthData);
      setDetections(detectionsData);

      if (detectionsData.length > 0 && !activeDetection) {
        setActiveDetection(detectionsData[0]);
      }
    } catch (err) {
      console.error("Error loading dashboard data:", err);
    } finally {
      setIsRefreshing(false);
    }
  }, [activeDetection]);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Server-Sent Events (SSE) Live Real-Time Stream
  useEffect(() => {
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource("/api/stream");

      eventSource.addEventListener("connected", () => {
        setSseConnected(true);
      });

      eventSource.addEventListener("new_detection", (e: MessageEvent) => {
        try {
          const newDoc: DetectionItem = JSON.parse(e.data);
          if (newDoc && newDoc.object_name) {
            setActiveDetection(newDoc);
            setDetections((prev) => [
              newDoc,
              ...prev.filter((d) => d.timestamp !== newDoc.timestamp),
            ]);
          }
        } catch (err) {
          console.error("Failed to parse SSE new_detection:", err);
        }
      });

      eventSource.onerror = () => {
        setSseConnected(false);
      };
    } catch (err) {
      console.error("Could not initialize EventSource:", err);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  // Periodic heartbeat polling as fallback (every 10 seconds)
  useEffect(() => {
    const pollInterval = setInterval(() => {
      getSystemHealth().then(setHealth);
    }, 10000);

    return () => clearInterval(pollInterval);
  }, []);

  // Handle new scan completed by browser webcam
  const handleScanComplete = (newItem: DetectionItem) => {
    setActiveDetection(newItem);
    setDetections((prev) => [newItem, ...prev.filter((d) => d.timestamp !== newItem.timestamp)]);
  };

  // Handle search query
  const handleSearch = async (query: string) => {
    const results = await searchDetections(query);
    setDetections(results);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#070b14] text-slate-100 font-sans">
      {/* Top Navbar */}
      <Navbar health={health} onRefresh={loadData} isLoading={isRefreshing} />

      {/* Main Dashboard Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-8 flex flex-col gap-6">
        {/* Top KPI Stats Bar */}
        <StatsCards
          detections={detections}
          modelId={health?.model_id}
          telemetry={health?.telemetry}
        />

        {/* Core Visual Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Webcam HUD & Scan Controls (7 cols) */}
          <section className="lg:col-span-7 flex flex-col gap-4">
            <WebcamHUD
              onScanComplete={handleScanComplete}
              isAnalyzing={isAnalyzing}
              setIsAnalyzing={setIsAnalyzing}
            />

            {/* Quick Keyboard Hints & Status */}
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-slate-900/40 border border-slate-800 text-slate-400 font-mono text-[11px]">
              <span>
                Controls: <kbd className="text-cyan-300 font-bold">SPACE</kbd> Capture |{" "}
                <kbd className="text-cyan-300 font-bold">A</kbd> Auto-Scan (8s) |{" "}
                <span className="text-amber-400 font-bold">👍</span> Gesture
              </span>
              <span className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    sseConnected ? "bg-emerald-400 animate-pulse" : "bg-slate-500"
                  }`}
                />
                <span>SSE Stream: {sseConnected ? "ONLINE (Live)" : "POLLING"}</span>
              </span>
            </div>
          </section>

          {/* Right Column: Multi-Agent Analysis & History (5 cols) */}
          <section className="lg:col-span-5 flex flex-col gap-5">
            {/* Latest AI Perception & Enrichment Summary */}
            <LatestAnalysis detection={activeDetection} />

            {/* MongoDB Historical Scan Log */}
            <DetectionHistory
              detections={detections}
              activeItem={activeDetection}
              onSelectDetection={setActiveDetection}
              onSearch={handleSearch}
            />
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="glass-panel border-t border-slate-800/80 py-4 px-6 text-center text-xs font-mono text-slate-500">
        <p>
          Smart Camera Vision Recognition v2.0 • Powered by Agno Multi-Agent Architecture, Google Gemini
          3.5 Flash Lite, Edge TTS & MongoDB Atlas
        </p>
      </footer>
    </div>
  );
}
