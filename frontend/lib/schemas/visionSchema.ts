import { z } from "zod";

export const SpatialBoundingBoxSchema = z.object({
  label: z.string(),
  confidence: z.number().min(0).max(1),
  x_min: z.number().min(0).max(1),
  y_min: z.number().min(0).max(1),
  x_max: z.number().min(0).max(1),
  y_max: z.number().min(0).max(1),
  pan_x: z.number().min(-1).max(1).default(0),
  depth_z: z.number().default(-1),
});

export const ProductPriceInfoSchema = z.object({
  model_name: z.string(),
  estimated_price_ils: z.string().nullable().optional(),
  specs_summary: z.string().nullable().optional(),
  source_url: z.string().url().nullable().optional(),
  bbox: SpatialBoundingBoxSchema.nullable().optional(),
  store_name: z.string().nullable().optional(),
  price_screenshot_base64: z.string().nullable().optional(),
});

export const SceneDeltaReportSchema = z.object({
  added_entities: z.array(z.string()).default([]),
  removed_entities: z.array(z.string()).default([]),
  dwell_time_seconds: z.number().nullable().optional(),
  delta_summary_hebrew: z.string().nullable().optional(),
});

export const CompareAnalysisResultSchema = z.object({
  item_a_name: z.string(),
  item_b_name: z.string(),
  price_a_ils: z.string().nullable().optional(),
  price_b_ils: z.string().nullable().optional(),
  comparison_points: z.array(z.record(z.string())).default([]),
  winner_recommendation_hebrew: z.string(),
});

export const AskVisionRequestSchema = z.object({
  image: z.string().min(50),
  question_hebrew: z.string().min(2).max(500),
  zone_polygon: z.array(z.object({ x: z.number(), y: z.number() })).optional(),
});

export const AskVisionResponseSchema = z.object({
  question_hebrew: z.string(),
  answer_hebrew: z.string(),
  tts_audio_base64: z.string().nullable().optional(),
  pan_x: z.number().default(0),
  referenced_entities: z.array(z.string()).default([]),
});

export type SpatialBoundingBox = z.infer<typeof SpatialBoundingBoxSchema>;
export type ProductPriceInfo = z.infer<typeof ProductPriceInfoSchema>;
export type SceneDeltaReport = z.infer<typeof SceneDeltaReportSchema>;
export type CompareAnalysisResult = z.infer<typeof CompareAnalysisResultSchema>;
export type AskVisionResponse = z.infer<typeof AskVisionResponseSchema>;
