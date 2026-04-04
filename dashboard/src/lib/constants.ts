export const MAP_CENTER: [number, number] = [36.0, 127.5];
export const MAP_ZOOM = 7;

export const TILE_URL =
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://carto.com/">CARTO</a>';

export const KOREAN_AIRLINES: Record<string, string> = {
  KE: "대한항공",
  OZ: "아시아나항공",
  LJ: "진에어",
  "7C": "제주항공",
  TW: "티웨이항공",
  ZE: "이스타항공",
  BX: "에어부산",
  RS: "에어서울",
};

export const KOREAN_AIRPORTS: Record<string, string> = {
  ICN: "인천",
  GMP: "김포",
  PUS: "김해",
  CJU: "제주",
  TAE: "대구",
  KWJ: "광주",
  RSU: "여수",
  USN: "울산",
  MWX: "무안",
  YNY: "양양",
};

export const SEVERITY_COLORS: Record<string, string> = {
  HIGH: "#ef4444",
  MEDIUM: "#fbbf24",
  LOW: "#38bdf8",
};

export const RISK_COLORS: Record<string, string> = {
  critical: "#ef4444",
  warning: "#fbbf24",
  normal: "#22c55e",
};
