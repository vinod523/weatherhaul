# WeatherHaul

React + Django truck routing prototype: compare three routes, evaluate weather at estimated checkpoint arrival times, apply load rules, and explore a 0–48-hour forecast corridor.

**Hosted interface:** https://weatherhaul-route-planner.vnodkumars.chatgpt.site (owner-private Sites preview; illustrative weather).

The preview contains a clearly labeled sample on real OSRM road geometry. Live route planning is implemented in Django; deploy the Docker image to a Python host and connect its URL through **Connection settings** in the preview, or serve the complete app from Django on one host.

## Run locally

Requires Node 22+, pnpm 11.25, Python 3.12+.

```sh
corepack enable
pnpm install --frozen-lockfile
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python backend/manage.py runserver
```

In another terminal:

```sh
pnpm dev
```

Open http://127.0.0.1:5173. Select **Live API**, fill in the form and submit. Vite proxies `/api` to Django at port 8000. No API keys are required for the public evaluation providers.

## Deploy the complete React + Django app

The included `render.yaml` creates a Docker web service on Render. Create a Render Blueprint from this GitHub repository. It builds React, installs Django, collects static assets and starts Gunicorn. Set `ALLOWED_HOSTS` if using a custom domain; set `CORS_ALLOWED_ORIGINS` if serving the React interface on a different origin. The Blueprint generates a Django secret automatically.

Alternatively:

```sh
docker build -t weatherhaul .
docker run --rm -p 8000:8000 -e DJANGO_SECRET_KEY=replace-with-a-random-secret -e ALLOWED_HOSTS=localhost,127.0.0.1 weatherhaul
```

Visit http://localhost:8000 and select **Live API**. Django serves the built React application and its API on the same origin. No database is needed: this app does not store driver trips. Forecast responses use a ten-minute process cache.

Deployment of the Django service requires a hosting account. The Sites preview hosts static React; it cannot run a Django process. See [walkthrough](docs/WALKTHROUGH.md) for a 7-minute recording script.

## API

`GET /api/health` → `{ "status": "ok", "service": "weatherhaul-django" }`

`POST /api/plan` (JSON):

```json
{
  "origin": "Denver, CO",
  "destination": "Kansas City, MO",
  "departure": "2026-10-29T14:00:00-06:00",
  "load": 32000,
  "spacing": 25
}
```

Use a current, timezone-aware departure (now to +96 hours). Load is 0–100,000 lb; spacing is 10, 25 or 50 miles. Successful responses contain all route geometries, checkpoint weather and ETAs, risk miles, average risks, eligibility, the recommended route ID (or null), and a corridor lattice with 49 hourly forecasts. Invalid inputs return 400; upstream provider/forecast gaps return 502. Missing weather is never classified as Low.

### Risk rules and boundaries

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | <25 | 25–<35 | 35–<45 | 45–<55 | ≥55 |
| Rain (in/hr) | <0.10 | 0.10–<0.25 | 0.25–<0.50 | 0.50–1.00 | >1.00 |
| Snow (in/hr) | <0.5 | 0.5–<1.0 | 1.0–<2.0 | 2.0–3.0 | >3.0 |

The brief overlaps rain/snow boundaries. At shared endpoints we choose the higher category, except 1.00 rain and 3.0 snow remain Severe because No Travel explicitly requires greater than those values. Wind is continuous (34.9 stays Moderate).

Load rules use strict weight comparisons: wind ≥55 → No Travel; wind ≥45 with load >30,000 lb → No Travel; wind ≥35 with load >40,000 lb → at least Severe. The highest condition determines checkpoint risk.

### Sampling and recommendation

1. Open-Meteo geocodes the two locations. OSRM requests three alternatives. If fewer return, additional actual API routes through corridor-offset waypoints are requested; if three distinct routes still cannot be found, the API returns the available routes and a warning rather than fabricated options.
2. Full route annotations provide each road segment's distance and duration. Checkpoints are interpolated every requested number of miles, always including both endpoints. Arrival times use cumulative annotated durations scaled to the route total to include turn costs, not a single average trip speed.
3. Forecasts are batched in groups of 35 with three concurrent requests. Requested units are mph and inches, and response unit metadata is validated. Snowfall is converted from cm only when the provider reports cm. Rain includes showers.
4. Precipitation is a preceding-hour total. Each ETA is converted to UTC and matched to its containing forecast interval using the next hourly boundary (an exact hour uses itself).
5. Each segment uses the worse of its endpoint risks; risk miles sum the actual segment lengths. Average risk is distance-weighted on scores 0–4. This is a conservative sampled estimate, not a guarantee about unobserved weather between checkpoints.
6. Routes containing any No Travel miles are ineligible. Eligible routes are ranked lexicographically by Severe miles, High miles, average risk, then duration. If every route is ineligible, recommendation is null.
7. A 6×10 forecast lattice covers the route bounding corridor. The map draws radial weather intensity on a canvas; slider changes redraw the already fetched forecast. There are no slider-triggered network requests. The 49 time steps are relative to departure. The slider does not recalculate the ETA-based recommendation.

## Verification

```sh
.venv/bin/python backend/manage.py test routing -v 2
.venv/bin/python backend/manage.py check
pnpm test
pnpm build
```

Tests cover wind/load and precipitation boundaries, invalid/nonfinite data, distance weighting, all four ranking tie-breakers, No Travel exclusion, segment-duration checkpoint interpolation, forecast interval and unit conversion, request validation and upstream errors. A live provider integration was also exercised for Denver → Kansas City.

## Structure

- `frontend/src/main.jsx`: planner, route comparison, Leaflet map, canvas weather overlay, forecast playback and checkpoint table.
- `frontend/src/risk.js`: sample-mode risk logic, with matching tests.
- `frontend/src/demo.json`: checked-in illustrative weather and real OSRM route geometry; sample-mode departures rebase ETA labels and do not turn illustrative weather into forecasts.
- `backend/routing/services.py`: provider calls, checkpoints, forecast alignment, corridor data.
- `backend/routing/risk.py`: authoritative live risk and recommendation logic.
- `backend/routing/views.py`: request validation and API errors.

## Limits

OSRM's public driving profile does **not** enforce truck height, weight, axle, hazmat or road restrictions. ETAs exclude live traffic and driver rest requirements. This is an evaluation prototype and needs a truck-capable routing provider plus operational validation before real dispatch use. Public provider availability/rate limits apply; a failed forecast fails the plan instead of silently substituting sample data. City geocoding takes the provider's first match; use city/state/country to disambiguate.

Weather requests are capped at 220 checkpoints per route. Larger trips must use wider spacing. The rectangular lattice is an approximate weather surface; point forecasts remain inspectable at checkpoints. No authentication, persistent trip history, billing or tracking is added. Public deployments should put provider quotas and request throttling at the edge.

## Data attribution

Routing: [OSRM](https://project-osrm.org/docs/v5.24.0/api/). Forecasts and city search: [Open-Meteo](https://open-meteo.com/en/docs), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Basemap: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). Map rendering: [Leaflet](https://leafletjs.com/).
