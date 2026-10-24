"use client";

import React, { useEffect, useRef } from "react";
import { SpatialBoundingBox } from "../lib/schemas/visionSchema";

interface VisionCanvasOverlayProps {
  bboxes?: SpatialBoundingBox[];
  gestureDetected?: string | null;
  width?: number;
  height?: number;
  activeZoneName?: string;
}

export default function VisionCanvasOverlay({
  bboxes = [],
  gestureDetected,
  width = 1280,
  height = 720,
  activeZoneName = "אזור מעקב פעיל (Zone A)",
}: VisionCanvasOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const w = canvas.width;
      const h = canvas.height;

      // 1. Draw Subtle Target Crosshairs in Center
      const cx = w / 2;
      const cy = h / 2;
      ctx.strokeStyle = "rgba(56, 189, 248, 0.25)";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cx - 30, cy);
      ctx.lineTo(cx + 30, cy);
      ctx.moveTo(cx, cy - 30);
      ctx.lineTo(cx, cy + 30);
      ctx.stroke();
      ctx.setLineDash([]);

      // 2. Draw Spatial Bounding Boxes
      bboxes.forEach((box) => {
        const bx = box.x_min * w;
        const by = box.y_min * h;
        const bw = (box.x_max - box.x_min) * w;
        const bh = (box.y_max - box.y_min) * h;

        // Box border with glow
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2;
        ctx.shadowColor = "#0284c7";
        ctx.shadowBlur = 8;
        ctx.strokeRect(bx, by, bw, bh);
        ctx.shadowBlur = 0;

        // Corner brackets
        const cornerLen = Math.min(18, bw / 4, bh / 4);
        ctx.strokeStyle = "#a855f7";
        ctx.lineWidth = 3;
        ctx.beginPath();
        // Top-left
        ctx.moveTo(bx, by + cornerLen);
        ctx.lineTo(bx, by);
        ctx.lineTo(bx + cornerLen, by);
        // Top-right
        ctx.moveTo(bx + bw - cornerLen, by);
        ctx.lineTo(bx + bw, by);
        ctx.lineTo(bx + bw, by + cornerLen);
        // Bottom-left
        ctx.moveTo(bx, by + bh - cornerLen);
        ctx.lineTo(bx, by + bh);
        ctx.lineTo(bx + cornerLen, by + bh);
        // Bottom-right
        ctx.moveTo(bx + bw - cornerLen, by + bh);
        ctx.lineTo(bx + bw, by + bh);
        ctx.lineTo(bx + bw, by + bh - cornerLen);
        ctx.stroke();

        // Label Tag
        const tagText = `${box.label} (${Math.round(box.confidence * 100)}%)`;
        ctx.font = "bold 13px system-ui, sans-serif";
        const textWidth = ctx.measureText(tagText).width;

        ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
        ctx.fillRect(bx, Math.max(0, by - 24), textWidth + 16, 22);

        ctx.fillStyle = "#38bdf8";
        ctx.fillText(tagText, bx + 8, Math.max(16, by - 8));

        // Spatial Audio Indicator (3D Pan marker)
        const panPct = Math.round(((box.pan_x + 1) / 2) * 100);
        ctx.fillStyle = "#e2e8f0";
        ctx.font = "10px monospace";
        ctx.fillText(`🔊 3D Pan: ${panPct}%`, bx + 8, by + bh + 14);
      });

      // 3. Gesture Badge
      if (gestureDetected) {
        ctx.fillStyle = "rgba(16, 185, 129, 0.9)";
        ctx.beginPath();
        ctx.roundRect(16, 16, 210, 36, 8);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 13px system-ui, sans-serif";
        ctx.fillText(`מחווה: ${gestureDetected}`, 28, 40);
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [bboxes, gestureDetected, width, height]);

  return (
    <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden">
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="w-full h-full object-cover transform-gpu"
      />
      <div className="absolute top-3 right-3 bg-slate-900/80 backdrop-blur border border-cyan-500/30 text-cyan-400 text-xs px-2.5 py-1 rounded-full font-mono flex items-center gap-1.5 shadow-lg">
        <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
        <span>{activeZoneName}</span>
      </div>
    </div>
  );
}
