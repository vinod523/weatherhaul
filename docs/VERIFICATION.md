# Verification record

Verified on 2026-10-29.

- Django test suite: 11 tests passed; no system check issues.
- JavaScript risk suite: 4 tests passed.
- Vite production build: passed.
- Real upstream integration: Denver, CO → Kansas City, MO, departure one hour ahead, 32,000 lb, 50-mile spacing. Returned 3 routes, 14 checkpoints per route, 60 corridor points and 49 hourly forecasts per corridor point in 5.6 seconds. All three had Low peak risk at the time of the run. Provider forecasts change.
- Browser inspection: base map rendered; route selection updated selected route and checkpoint risks. Rain overlay selected and rendered. Sample data visibly labeled illustrative. All checkpoints available in the scrollable table and map.
- Django static asset collection and health endpoint: passed.

Tests explicitly cover endpoint ETA normalization to routing duration, UTC offsets, snowfall in both cm and inches, unavailable/null forecasts, precipitation shared boundaries, strict load thresholds and all recommendation tie-breakers.

Docker image build and a persistent hosted Django service have not been verified. Docker configuration and Render Blueprint are supplied. The available Sites runtime serves the React preview; it does not execute Django. No Loom recording has been made; the 7-minute script is supplied.
