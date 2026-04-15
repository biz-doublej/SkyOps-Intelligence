"""SkyOps Feast entities (P6-A).

Entities are "things we have features about":
  - Flight (entity key: flight_id)
  - Aircraft (entity key: tail_number)
  - Airport (entity key: airport_code)
  - ICAO24 (entity key: icao24) — for live ADS-B lookups
"""
from __future__ import annotations

from feast import Entity, ValueType


flight_entity = Entity(
    name="flight",
    join_keys=["flight_id"],
    value_type=ValueType.STRING,
    description="One flight leg (tail + origin + destination + scheduled_out)",
)

aircraft_entity = Entity(
    name="aircraft",
    join_keys=["tail_number"],
    value_type=ValueType.STRING,
    description="Physical airframe by registration (e.g. 'N12345', 'HL7707')",
)

airport_entity = Entity(
    name="airport",
    join_keys=["airport_code"],
    value_type=ValueType.STRING,
    description="ICAO 4-letter airport code (e.g. 'RKSI', 'KATL', 'EGLL')",
)

icao24_entity = Entity(
    name="icao24",
    join_keys=["icao24"],
    value_type=ValueType.STRING,
    description="Mode-S transponder hex address from ADS-B (6 hex chars)",
)
