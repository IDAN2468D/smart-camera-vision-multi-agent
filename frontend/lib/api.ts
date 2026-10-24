import {
  SpatialBoundingBox,
  SceneDeltaReport,
  CompareAnalysisResult,
  AskVisionResponse,
  AskVisionResponseSchema,
  CompareAnalysisResultSchema,
  SceneDeltaReportSchema
} from "./schemas/visionSchema";

export type { SpatialBoundingBox, SceneDeltaReport, CompareAnalysisResult, AskVisionResponse };

// When running in browser, use relative URL to route through Next.js proxy to backend
const API_BASE_URL = typeof window !== "undefined" ? "" : (process.env.BACKEND_URL || "http://127.0.0.1:5000");

export interface ProductPriceInfo {
  model_name: string;
  estimated_price_ils?: string | null;
  specs_summary?: string | null;
  source_url?: string | null;
}

export interface DetectionItem {
  object_name: string;
  category: string;
  detected_entities?: string[];
  face_detected?: boolean;
  hands_detected?: boolean;
  detected_text?: string | null;
  confidence: number;
  visual_description: string;
  enrichment_summary: string;
  timestamp: string;
  trigger_source?: string;
  gesture_detected?: string | null;
  recognized_person_name?: string | null;
  product_info?: ProductPriceInfo | null;
  thumbnail_base64?: string | null;
  tts_audio_base64?: string | null;
  similarity_score?: number;
  embedding_model?: string;
  human_evaluated?: boolean;
  human_verified?: boolean;
  spatial_bboxes?: SpatialBoundingBox[];
  scene_delta?: SceneDeltaReport | null;
}

export interface TelemetryMetrics {
  total_scans: number;
  avg_latency_ms: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: string;
  estimated_cost_ils: string;
  cost_per_scan_ils: string;
  human_evaluations_count: number;
}

export interface HealthResponse {
  status: "online" | "degraded";
  database: "connected" | "disconnected";
  database_name: string;
  collection_name: string;
  model_id: string;
  features?: Record<string, boolean>;
  telemetry?: TelemetryMetrics;
}

export async function getSystemHealth(): Promise<HealthResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    return null;
  }
}

export async function fetchRecentDetections(limit: number = 20): Promise<DetectionItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/detections?limit=${limit}`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.data || [];
  } catch (error) {
    console.error("Failed to fetch detections:", error);
    return [];
  }
}

export async function searchDetections(query: string): Promise<DetectionItem[]> {
  try {
    if (!query.trim()) return await fetchRecentDetections();
    const res = await fetch(`${API_BASE_URL}/api/detections/search?q=${encodeURIComponent(query)}`, { cache: "no-store" });
    if (!res.ok) return [];
    const data = await res.json();
    return data.data || [];
  } catch (error) {
    console.error("Search failed:", error);
    return [];
  }
}

export async function searchSimilarDetections(
  query: string,
  limit: number = 10,
  minScore: number = 0.0
): Promise<DetectionItem[]> {
  try {
    if (!query.trim()) return await fetchRecentDetections();
    const res = await fetch(
      `${API_BASE_URL}/api/detections/similar?q=${encodeURIComponent(query)}&limit=${limit}&min_score=${minScore}`,
      { cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.data || [];
  } catch (error) {
    console.error("Semantic search failed:", error);
    return [];
  }
}

export async function analyzeImageFrame(
  imageBase64: string,
  triggerSource: string = "web_hud",
  gestureDetected?: string
): Promise<DetectionItem | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image: imageBase64,
        trigger_source: triggerSource,
        gesture_detected: gestureDetected
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `Server error: ${res.status}`);
    }

    const data = await res.json();
    return data.data;
  } catch (error) {
    console.error("Error analyzing frame:", error);
    throw error;
  }
}

export function getExportUrl(format: "excel" | "pdf", limit: number = 50): string {
  return `${API_BASE_URL}/api/export?format=${format}&limit=${limit}`;
}

export async function enrollFaceProfile(name: string, role?: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/faces/enroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, role }),
    });
    return res.ok;
  } catch (error) {
    console.error("Face enrollment failed:", error);
    return false;
  }
}

export async function submitHumanFeedback(
  timestamp: string,
  isAccurate: boolean,
  correctedLabel?: string,
  notes?: string
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/detections/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        timestamp,
        is_accurate: isAccurate,
        corrected_label: correctedLabel,
        notes
      }),
    });
    return res.ok;
  } catch (error) {
    console.error("Failed to submit human feedback:", error);
    return false;
  }
}

export async function fetchTelemetryMetrics(): Promise<TelemetryMetrics | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/metrics`, { cache: "no-store" });
    if (!res.ok) return null;
    const data = await res.json();
    return data.metrics;
  } catch (error) {
    return null;
  }
}

export async function askVisionLive(
  image: string,
  questionHebrew: string
): Promise<AskVisionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image, question_hebrew: questionHebrew }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || "Failed to process visual question");
  }
  const payload = await res.json();
  return AskVisionResponseSchema.parse(payload.data);
}

export async function compareProducts(
  imageA: string,
  imageB?: string,
  labelA?: string,
  labelB?: string
): Promise<CompareAnalysisResult> {
  const res = await fetch(`${API_BASE_URL}/api/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_a: imageA,
      image_b: imageB,
      label_a: labelA,
      label_b: labelB,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || "Failed to compare products");
  }
  const payload = await res.json();
  return CompareAnalysisResultSchema.parse(payload.data);
}

export async function getSceneZoneDiff(
  image?: string,
  zoneId: string = "default_zone"
): Promise<SceneDeltaReport> {
  const res = await fetch(`${API_BASE_URL}/api/zones/diff`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image, zone_id: zoneId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || "Failed to compute scene delta");
  }
  const payload = await res.json();
  return SceneDeltaReportSchema.parse(payload.data.delta);
}
