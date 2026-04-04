import type { AircraftState, AnomalyEvent } from "./types";

const callsigns = [
  "KE901", "KE123", "OZ351", "OZ702", "LJ502",
  "7C201", "TW901", "ZE301", "BX101", "RS401",
  "KE651", "OZ111", "LJ701", "7C503", "TW302",
  "KE805", "OZ222", "BX205", "RS102", "ZE405",
];

export function generateMockAircraft(): AircraftState[] {
  const now = Math.floor(Date.now() / 1000);
  return callsigns.map((callsign, i) => ({
    icao24: `mock${i.toString().padStart(4, "0")}`,
    callsign,
    latitude: 33.5 + Math.random() * 5.5,
    longitude: 124.5 + Math.random() * 5.5,
    baro_altitude: 3000 + Math.random() * 9000,
    velocity: 180 + Math.random() * 80,
    on_ground: false,
    true_track: Math.random() * 360,
    vertical_rate: (Math.random() - 0.5) * 10,
    updated_at: now - Math.floor(Math.random() * 30),
  }));
}

export function generateMockAnomalies(): AnomalyEvent[] {
  const types: AnomalyEvent["anomaly_type"][] = [
    "ALTITUDE_SPIKE", "VELOCITY_SPIKE", "PATH_DEVIATION",
  ];
  const severities: AnomalyEvent["severity"][] = ["HIGH", "MEDIUM", "LOW"];
  const now = Math.floor(Date.now() / 1000);

  return Array.from({ length: 10 }, (_, i) => ({
    icao24: `mock${i.toString().padStart(4, "0")}`,
    callsign: callsigns[i % callsigns.length],
    anomaly_type: types[i % 3],
    severity: severities[i % 3],
    description: [
      "급격한 고도 변화 감지",
      "비정상 속도 변화 감지",
      "경로 이탈 감지",
    ][i % 3],
    latitude: 33.5 + Math.random() * 5.5,
    longitude: 124.5 + Math.random() * 5.5,
    altitude_m: 3000 + Math.random() * 9000,
    velocity_m_s: 80 + Math.random() * 50,
    detected_at: now - i * 45,
  }));
}
