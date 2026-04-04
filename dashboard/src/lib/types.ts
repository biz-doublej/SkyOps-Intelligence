// Backend data types matching serving/api.py and pipeline schemas

export interface AircraftState {
  icao24: string;
  callsign: string;
  latitude: number;
  longitude: number;
  baro_altitude: number;
  velocity: number;
  on_ground: boolean;
  true_track: number;
  vertical_rate: number;
  updated_at: number;
}

export interface AnomalyEvent {
  icao24: string;
  callsign: string;
  anomaly_type: "ALTITUDE_SPIKE" | "VELOCITY_SPIKE" | "PATH_DEVIATION";
  severity: "LOW" | "MEDIUM" | "HIGH";
  description: string;
  latitude: number;
  longitude: number;
  altitude_m: number;
  velocity_m_s: number;
  detected_at: number;
  details?: Record<string, unknown>;
}

export interface DelayRequest {
  dep_hour: number;
  dep_minute: number;
  dep_dayofweek: number;
  dep_month: number;
  dep_dayofyear: number;
  is_weekend: number;
  distance_miles: number;
  sched_elapsed_min: number;
  prev_dep_delay_min: number;
  prev_arr_delay_min: number;
  is_prev_delayed: number;
  origin_hourly_departures: number;
  dest_hourly_arrivals: number;
  dep_month_weather_score: number;
  origin_weather_hist_delay: number;
  dest_weather_hist_delay: number;
  carrier_hist_delay: number;
  origin_hist_delay: number;
  dest_hist_delay: number;
  route_hist_delay: number;
  carrier_code: string;
  origin: string;
  dest: string;
}

export interface DelayResponse {
  predicted_delay_min: number;
  is_delayed: boolean;
  confidence: "high" | "medium" | "low";
  latency_ms: number;
}

export interface AnomalyRequest {
  features: number[];
  flight_id?: string;
}

export interface AnomalyResponse {
  flight_id: string | null;
  anomaly_score: number;
  is_anomaly: boolean;
  risk_level: "critical" | "warning" | "normal";
  latency_ms: number;
}

export interface ChatRequest {
  question: string;
  use_rag?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: Array<{
    source: string;
    section: string;
    domain: string;
    text: string;
  }>;
  latency_ms: number;
  rag_used: boolean;
}

export interface HealthResponse {
  status: string;
  models: {
    xgboost: boolean;
    isolation_forest: boolean;
    rag_chain: boolean;
  };
  prometheus: boolean;
  vllm_url: string;
}
