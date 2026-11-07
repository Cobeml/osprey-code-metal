#!/usr/bin/env python3
"""Fetch an Open-Meteo forcing snapshot for Massachusetts Bay into fixtures/env/.

Wind: forecast API, 10 m wind speed (m/s) and direction (degrees, meteorological FROM).
Current: marine API, ocean_current_velocity and ocean_current_direction (direction the current
flows TOWARD, per Open-Meteo docs). Velocity is requested in m/s where supported; otherwise
km/h is converted.
Usage: python3 scripts/fetch_env.py [lat] [lon]
"""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

LAT = float(sys.argv[1]) if len(sys.argv) > 1 else 42.35
LON = float(sys.argv[2]) if len(sys.argv) > 2 else -70.80
ROOT = Path(__file__).resolve().parents[1]

FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            "&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&forecast_days=2&timezone=UTC")
MARINE = ("https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}"
          "&hourly=ocean_current_velocity,ocean_current_direction&forecast_days=2&timezone=UTC")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "osprey-hackathon/0.1"})
    return json.load(urllib.request.urlopen(req, timeout=20))


def main():
    f_url, m_url = FORECAST.format(lat=LAT, lon=LON), MARINE.format(lat=LAT, lon=LON)
    f, m = get(f_url), get(m_url)
    fh, mh = f["hourly"], m["hourly"]
    unit = m.get("hourly_units", {}).get("ocean_current_velocity", "km/h")
    scale = 1 / 3.6 if unit.replace(" ", "") in ("km/h", "kmh") else 1.0
    times = [t for t in fh["time"] if t in set(mh["time"])]
    fi = {t: i for i, t in enumerate(fh["time"])}
    mi = {t: i for i, t in enumerate(mh["time"])}
    now = dt.datetime.now(dt.timezone.utc)
    start = now.strftime("%Y-%m-%dT%H:00")
    times = [t for t in times if t >= start][:24] or times[:24]

    def col(src, idx, key, s=1.0, default=0.0):
        out = []
        for t in times:
            v = src[key][idx[t]]
            out.append(default if v is None else round(v * s, 4))
        return out

    data = {
        "provenance": {
            "source": "Open-Meteo (open-meteo.com), CC BY 4.0",
            "forecast_url": f_url, "marine_url": m_url,
            "fetched_utc": now.isoformat(timespec="seconds"),
            "lat": LAT, "lon": LON,
            "current_velocity_unit_original": unit,
            "notes": "wind direction = FROM (meteorological); current direction = TOWARD",
        },
        "hourly": {
            "time": times,
            "wind_speed_10m": col(fh, fi, "wind_speed_10m"),
            "wind_direction_10m": col(fh, fi, "wind_direction_10m"),
            "ocean_current_velocity": col(mh, mi, "ocean_current_velocity", scale),
            "ocean_current_direction": col(mh, mi, "ocean_current_direction"),
        },
    }
    out = ROOT / "fixtures/env" / f"massbay-{now:%Y%m%d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1))
    h = data["hourly"]
    print(f"wrote {out}: {len(times)} h from {times[0]}; wind {h['wind_speed_10m'][0]} m/s from "
          f"{h['wind_direction_10m'][0]}°, current {h['ocean_current_velocity'][0]} m/s toward "
          f"{h['ocean_current_direction'][0]}° ({unit} originally)")


if __name__ == "__main__":
    main()
