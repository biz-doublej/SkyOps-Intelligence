"use client";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { AircraftState } from "@/lib/types";
import { MAP_CENTER, MAP_ZOOM, TILE_URL, TILE_ATTRIBUTION } from "@/lib/constants";

function createAircraftIcon(heading: number) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="transform:rotate(${heading}deg)"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>`;
  return L.divIcon({
    html: svg,
    className: "",
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

interface Props {
  aircraft: AircraftState[];
}

export default function AircraftMap({ aircraft }: Props) {
  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={MAP_ZOOM}
      className="h-full w-full rounded-xl"
      zoomControl={true}
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      {aircraft
        .filter((a) => a.latitude && a.longitude)
        .map((a) => (
          <Marker
            key={a.icao24}
            position={[a.latitude, a.longitude]}
            icon={createAircraftIcon(a.true_track || 0)}
          >
            <Popup>
              <div className="text-sm space-y-1">
                <div className="font-bold text-sky-400">
                  {a.callsign || a.icao24}
                </div>
                <div>고도: {Math.round(a.baro_altitude)}m</div>
                <div>속도: {Math.round(a.velocity)}m/s</div>
                <div>방향: {Math.round(a.true_track)}°</div>
                <div>수직속도: {a.vertical_rate?.toFixed(1)}m/s</div>
              </div>
            </Popup>
          </Marker>
        ))}
    </MapContainer>
  );
}
