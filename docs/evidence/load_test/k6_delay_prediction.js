// SkyOps Intelligence — k6 load test for /predict/delay (P8-E · 2026-04-15)
// ============================================================================
// Measures latency + throughput for XGBoost + Conformal prediction endpoint.
// Ramps from 0 → 50 VUs over 5 minutes, holds for 5 minutes, then ramps down.
//
// Thresholds (fail build if breached):
//   p95 < 500ms   (matches ADR-001 SLO)
//   p99 < 1000ms
//   error rate < 1%
//
// Run:
//   k6 run docs/evidence/load_test/k6_delay_prediction.js
//   k6 run --env BASE_URL=http://<NAS-IP>:8000 --out json=load_test_results.json ...
//
// Publish results:
//   k6 run ... --summary-export docs/evidence/load_test/summary.json

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const errorRate = new Rate("errors");
const delayLatency = new Trend("delay_p95_ms", true);

export const options = {
  stages: [
    { duration: "1m",  target: 10 },   // warmup
    { duration: "2m",  target: 30 },   // ramp
    { duration: "5m",  target: 50 },   // steady
    { duration: "2m",  target: 30 },   // cool
    { duration: "1m",  target: 0 },
  ],
  thresholds: {
    "http_req_duration{endpoint:delay}": ["p(95)<500", "p(99)<1000"],
    "errors": ["rate<0.01"],
    "checks": ["rate>0.99"],
  },
};

function randomDelayPayload() {
  const hour = Math.floor(Math.random() * 24);
  return {
    dep_hour: hour,
    dep_minute: Math.floor(Math.random() * 60),
    dep_dayofweek: Math.floor(Math.random() * 7),
    dep_month: 4,
    dep_dayofyear: 105,
    is_weekend: hour % 7 >= 5 ? 1 : 0,
    distance_miles: 200 + Math.random() * 2000,
    sched_elapsed_min: 60 + Math.random() * 240,
    prev_dep_delay_min: Math.random() * 20,
    prev_arr_delay_min: Math.random() * 15,
    is_prev_delayed: Math.random() > 0.8 ? 1 : 0,
    origin_hourly_departures: 15 + Math.floor(Math.random() * 30),
    dest_hourly_arrivals:    15 + Math.floor(Math.random() * 30),
    dep_month_weather_score: Math.random(),
    origin_weather_hist_delay: 3 + Math.random() * 8,
    dest_weather_hist_delay:   3 + Math.random() * 8,
    carrier_hist_delay: 5 + Math.random() * 8,
    origin_hist_delay:  4 + Math.random() * 8,
    dest_hist_delay:    4 + Math.random() * 8,
    route_hist_delay:   5 + Math.random() * 8,
    // P1 rotation features (optional, server-side defaults exist)
    rotation_depth: Math.floor(Math.random() * 4),
    prev_leg_arr_delay_min: Math.random() * 15,
    scheduled_turnaround_min: 35 + Math.random() * 30,
    actual_turnaround_min:   35 + Math.random() * 45,
    is_first_leg_of_day: Math.random() > 0.75 ? 1 : 0,
    // Categorical
    carrier_code: ["KE", "OZ", "7C", "LJ", "BX"][Math.floor(Math.random() * 5)],
    origin: ["ICN", "GMP", "CJU", "PUS"][Math.floor(Math.random() * 4)],
    dest:   ["CJU", "PUS", "ICN", "TAE", "KWJ"][Math.floor(Math.random() * 5)],
  };
}

export default function () {
  const payload = randomDelayPayload();

  // /predict/delay
  const delayRes = http.post(
    `${BASE_URL}/predict/delay`,
    JSON.stringify(payload),
    {
      headers: { "Content-Type": "application/json" },
      tags: { endpoint: "delay" },
    },
  );
  const delayOk = check(delayRes, {
    "delay 200 OK":           (r) => r.status === 200,
    "delay has prediction":   (r) => r.json("predicted_delay_min") !== undefined,
    "delay has interval":     (r) => r.json("prediction_interval") !== null,
    "delay latency < 500ms":  (r) => r.timings.duration < 500,
  });
  errorRate.add(!delayOk);
  delayLatency.add(delayRes.timings.duration);

  // /health (cheap — confirm no backpressure breaks healthchecks)
  const healthRes = http.get(`${BASE_URL}/health`, { tags: { endpoint: "health" } });
  check(healthRes, { "health 200": (r) => r.status === 200 });

  // jittered think time
  sleep(0.3 + Math.random() * 0.7);
}

export function handleSummary(data) {
  return {
    stdout: JSON.stringify({
      p50_ms: data.metrics.http_req_duration?.values["p(50)"],
      p95_ms: data.metrics.http_req_duration?.values["p(95)"],
      p99_ms: data.metrics.http_req_duration?.values["p(99)"],
      error_rate: data.metrics.errors?.values.rate,
      total_requests: data.metrics.http_reqs?.values.count,
    }, null, 2),
    "docs/evidence/load_test/summary.json": JSON.stringify(data, null, 2),
  };
}
