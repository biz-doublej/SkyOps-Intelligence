"use client";
import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { apiFetch } from "@/lib/api";

const STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const REFRESH_MS = 5000;

interface H3Cell {
  hex_id: string;
  latitude: number;
  longitude: number;
  count: number;
  avg_altitude: number;
  avg_velocity: number;
  callsigns: string[];
}

function toGeoJSON(data: H3Cell[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: data.map((d) => ({
      type: "Feature" as const,
      geometry: { type: "Point" as const, coordinates: [d.longitude, d.latitude] },
      properties: {
        count: d.count,
        avg_altitude: d.avg_altitude,
        avg_velocity: d.avg_velocity,
        callsigns: d.callsigns.join(", "),
      },
    })),
  };
}

export default function HeatmapGL() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [info, setInfo] = useState({ aircraft: 0, hexagons: 0 });

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: [127.5, 36.0],
      zoom: 6,
      pitch: 40,
    });
    mapRef.current = map;

    map.on("load", () => {
      map.addSource("h3-data", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      map.addLayer({
        id: "h3-heat",
        type: "heatmap",
        source: "h3-data",
        paint: {
          "heatmap-weight": ["interpolate", ["linear"], ["get", "count"], 1, 1, 3, 2, 5, 3],
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 4, 2, 7, 4, 10, 6],
          "heatmap-color": [
            "interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(15,23,42,0)",
            0.05, "#1e3a5f",
            0.15, "#0ea5e9",
            0.3, "#38bdf8",
            0.5, "#22d3ee",
            0.7, "#fbbf24",
            0.85, "#ef4444",
            1, "#ff2222",
          ],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 4, 60, 6, 80, 8, 100, 10, 120],
          "heatmap-opacity": 0.9,
        },
      });

      map.addLayer({
        id: "h3-circles",
        type: "circle",
        source: "h3-data",
        minzoom: 7,
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "count"], 1, 8, 5, 16, 10, 24],
          "circle-color": ["interpolate", ["linear"], ["get", "count"], 1, "#38bdf8", 3, "#fbbf24", 5, "#ef4444"],
          "circle-opacity": 0.7,
          "circle-stroke-width": 1,
          "circle-stroke-color": "#0f172a",
        },
      });

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
      map.on("mouseenter", "h3-circles", (e) => {
        map.getCanvas().style.cursor = "pointer";
        const f = e.features?.[0];
        if (!f || f.geometry.type !== "Point") return;
        const p = f.properties!;
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setHTML(
            `<div style="color:#f1f5f9;font-size:13px">
              <div style="font-weight:bold;color:#38bdf8;margin-bottom:4px">항공기 ${p.count}대</div>
              <div>평균 고도: ${Math.round(p.avg_altitude)}m</div>
              <div>평균 속도: ${Math.round(p.avg_velocity)}m/s</div>
              ${p.callsigns ? `<div style="color:#94a3b8;margin-top:4px;font-size:11px">${p.callsigns}</div>` : ""}
            </div>`
          )
          .addTo(map);
      });
      map.on("mouseleave", "h3-circles", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });

      let intervalId: ReturnType<typeof setInterval> | null = null;

      const fetchData = async () => {
        if (!mapRef.current) return;
        try {
          const src = mapRef.current.getSource("h3-data") as maplibregl.GeoJSONSource | undefined;
          if (!src) return;
          const data = await apiFetch<H3Cell[]>("/aircraft/h3?resolution=5");
          if (data.length > 0) {
            src.setData(toGeoJSON(data));
            const total = data.reduce((s, d) => s + d.count, 0);
            setInfo({ aircraft: total, hexagons: data.length });
          }
        } catch (e) {
          console.warn("H3 fetch failed:", e);
        }
      };

      fetchData();
      intervalId = setInterval(fetchData, REFRESH_MS);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute top-3 right-3 bg-[rgba(15,23,42,0.9)] border border-slate-700 rounded-lg px-4 py-3 text-sm">
        <div>
          추적 항공기: <span className="text-xl font-bold text-sky-400">{info.aircraft}</span>대
        </div>
        <div className="text-[11px] text-slate-500 mt-1">
          H3 Resolution 5 · {info.hexagons}개 헥사곤
        </div>
      </div>
    </div>
  );
}
