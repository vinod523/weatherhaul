# Loom walkthrough — 7 minute recording script

Recording status: a Loom video has not been recorded or uploaded. This script is ready to use once signed into Loom with screen/microphone access.

## 0:00–0:45 · The driver's decision

Open the hosted WeatherHaul interface. Explain the trip inputs: origin/destination, local departure time, load weight and weather checkpoint spacing. Point out the explicit illustrative-weather label in the hosted sample. Live planning uses the Django API rather than silently falling back to sample data.

## 0:45–1:45 · Compare the routes

Show the Denver → Kansas City sample. Explain the green recommendation. Select Northern bypass, then Southern corridor; the map and checkpoint table follow the selected route. Show travel time, distance, local arrival and the risk distribution strip. Explain why a faster route never overrides fewer Severe miles. The Southern sample is ineligible at 32,000 lb because of winds above 45 mph.

## 1:45–2:40 · Arrival-time checkpoints

Select the southern route, scroll to the checkpoint table and filter High risk & above. Click a row to fly to the checkpoint and click its map marker for weather details. Explain that each checkpoint's weather corresponds to its ETA, using cumulative road-segment durations. Set 10-mile sampling and recalculate to demonstrate the denser map, then return to 25 miles.

## 2:40–3:30 · Load-aware safety

Change the load to 30,000 lb exactly and recalculate. The southern corridor's ≥45 mph wind is Severe rather than No Travel; 30,001 lb crosses the strict load threshold. Show the methodology dialog for all thresholds. Explain that any route with No Travel miles is excluded entirely and all-blocked results produce an explicit travel advisory.

## 3:30–4:20 · Forecast corridor

Use Wind, Rain and Snow layers. Drag the slider to +24 hours and +48 hours; press Play to animate. Toggle the heatmap and use map zoom controls. Explain that the canvas redraws a preloaded lattice without fetching on slider movement. The slider shows a same-time weather surface; checkpoint risk and recommendation remain tied to vehicle arrival times.

## 4:20–5:25 · Live end-to-end planning

Start the local Django + React services or open the deployed Docker service. Select Live API, use a departure in the next hour, and plan Denver → Kansas City. Show the live forecast label, three route options (or provider warning), returned weather and ETAs. Demonstrate an invalid weight or unavailable provider error. If recording the static hosted sample without a backend, explicitly say live integration needs the Django host and show the API connection setting rather than claiming it is deployed.

## 5:25–6:30 · Implementation and correctness

Show `backend/routing/risk.py` (highest condition, load overrides, conservative segment risk, distance-weighted average and lexicographic ordering). Show `services.py` (annotated route sampling, UTC ETA forecast matching, validated units, batched cached provider requests). Run Python tests and the JavaScript risk tests. Show the Dockerfile and Render Blueprint for the complete same-origin app.

## 6:30–7:00 · Limits and next step

Explain the public OSRM driving profile: no truck-height/axle/hazmat enforcement, live traffic or rest scheduling. Forecasts are sampled estimates, not dispatch guarantees. Close with the GitHub repository and hosted preview links. Keep authentication screens and secrets out of the recording.
