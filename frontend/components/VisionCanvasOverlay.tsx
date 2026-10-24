"use client";

import React, { useEffect, useRef, useState } from "react";
import { SpatialBoundingBox } from "../lib/schemas/visionSchema";
import { liveVisionTracker } from "../lib/liveTracker";

interface VisionCanvasOverlayProps {
  videoRef?: React.RefObject<HTMLVideoElement>;
  bboxes?: SpatialBoundingBox[];
  gestureDetected?: string | null;
  width?: number;
  height?: number;
  activeZoneName?: string;
  isMirrored?: boolean;
}

export default function VisionCanvasOverlay({
  videoRef,
  bboxes = [],
  gestureDetected,
  width = 1280,
  height = 720,
  activeZoneName = "מעקב חי בזמן אמת (Live 60FPS)",
  isMirrored = false,
}: VisionCanvasOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeBoxes, setActiveBoxes] = useState<SpatialBoundingBox[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let frameCounter = 0;
    let currentLiveBoxes: SpatialBoundingBox[] = bboxes;

    const render = async () => {
      frameCounter++;

      // Run live tracker every 3 frames (~20Hz vision sample, 60Hz canvas draw)
      if (videoRef?.current && frameCounter % 3 === 0) {
        try {
          currentLiveBoxes = await liveVisionTracker.trackFrame(
            videoRef.current,
            bboxes,
            isMirrored
          );
          setActiveBoxes(currentLiveBoxes);
        } catch {
          currentLiveBoxes = bboxes;
        }
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width;
      const h = canvas.height;

      // 1. Center Crosshairs
      const cx = w / 2;
      const cy = h / 2;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.3)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx - 25, cy);
      ctx.lineTo(cx + 25, cy);
      ctx.moveTo(cx, cy - 25);
      ctx.lineTo(cx, cy + 25);
      ctx.stroke();
      ctx.setLineDash([]);

      // 2. Render Live Bounding Boxes
      const boxesToDraw = currentLiveBoxes.length > 0 ? currentLiveBoxes : bboxes;

      boxesToDraw.forEach((box, i) => {
        const bx = box.x_min * w;
        const by = box.y_min * h;
        const bw = Math.max(30, (box.x_max - box.x_min) * w);
        const bh = Math.max(30, (box.y_max - box.y_min) * h);

        const isFace = box.label.includes("Face");
        const isHand = box.label.includes("Hand");
        const themeColor = isFace ? "#38bdf8" : isHand ? "#f59e0b" : "#a855f7";
        const themeGlow = isFace ? "#0284c7" : isHand ? "#d97706" : "#7c3aed";

        // Bounding box border with glow
        ctx.strokeStyle = themeColor;
        ctx.lineWidth = 2;
        ctx.shadowColor = themeGlow;
        ctx.shadowBlur = 8;
        ctx.strokeRect(bx, by, bw, bh);
        ctx.shadowBlur = 0;

        // High-tech corner reticle brackets
        const cl = Math.min(18, bw / 3, bh / 3);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(bx, by + cl); ctx.lineTo(bx, by); ctx.lineTo(bx + cl, by);
        ctx.moveTo(bx + bw - cl, by); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw, by + cl);
        ctx.moveTo(bx, by + bh - cl); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + cl, by + bh);
        ctx.moveTo(bx + bw - cl, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by + bh - cl);
        ctx.stroke();

        // Label pill badge
        const tag = `${box.label} ${Math.round(box.confidence * 100)}%`;
        ctx.font = "bold 12px system-ui, sans-serif";
        const tw = ctx.measureText(tag).width;

        ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
        ctx.fillRect(bx, Math.max(0, by - 24), tw + 14, 20);

        ctx.fillStyle = themeColor;
        ctx.fillText(tag, bx + 6, Math.max(14, by - 9));

        // Spatial Audio Pan Indicator
        const panPct = Math.round(((box.pan_x + 1) / 2) * 100);
        ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
        ctx.font = "10px monospace";
        ctx.fillText(`🔊 3D Pan: ${panPct}%`, bx + 6, by + bh + 14);
      });

      // 3. Gesture Live Tag
      if (gestureDetected) {
        ctx.fillStyle = "rgba(16, 185, 129, 0.95)";
        ctx.beginPath();
        ctx.roundRect(16, 16, 200, 32, 8);
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px system-ui, sans-serif";
        ctx.fillText(`מחווה מזוהה: ${gestureDetected}`, 24, 38);
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [bboxes, gestureDetected, width, height, videoRef, isMirrored]);

  return (
    <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="w-full h-full object-cover transform-gpu"
      />
      {/* Live Indicator Pill */}
      <div className="absolute top-3 right-3 bg-slate-900/85 backdrop-blur border border-emerald-500/40 text-emerald-400 text-xs px-3 py-1 rounded-full font-mono flex items-center gap-2 shadow-lg">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
        <span className="font-semibold">{activeZoneName}</span>
      </div>
    </div>
  );
}
