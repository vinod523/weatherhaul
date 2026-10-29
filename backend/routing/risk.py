"""Continuous thresholds; ambiguous shared rain/snow endpoints use higher risk."""
import math
LEVELS = ['Low', 'Moderate', 'High', 'Severe', 'No Travel']

def classify(wind, rain, snow, load):
    if any(not math.isfinite(v) or v < 0 for v in (wind, rain, snow, load)):
        raise ValueError('Weather and load values must be finite and nonnegative.')
    wind_risk = sum(wind >= x for x in (25, 35, 45, 55))
    rain_risk = 4 if rain > 1 else 3 if rain >= .5 else 2 if rain >= .25 else 1 if rain >= .1 else 0
    snow_risk = 4 if snow > 3 else 3 if snow >= 2 else 2 if snow >= 1 else 1 if snow >= .5 else 0
    if wind >= 55 or (wind >= 45 and load > 30000):
        wind_risk = 4
    elif wind >= 35 and load > 40000:
        wind_risk = max(wind_risk, 3)
    return max(wind_risk, rain_risk, snow_risk)

def summarize(checkpoints):
    miles = [0.0] * 5
    for a, b in zip(checkpoints, checkpoints[1:]):
        # Conservative segment estimate: assign the worse endpoint to the whole segment.
        miles[max(a['risk'], b['risk'])] += b['mile'] - a['mile']
    total = sum(miles)
    return {'risk_miles': miles, 'average_risk': sum(i * m for i, m in enumerate(miles)) / total if total else 0, 'eligible': miles[4] == 0}

def recommend(routes):
    eligible = [r for r in routes if r['eligible']]
    return min(eligible, key=lambda r: (r['risk_miles'][3], r['risk_miles'][2], r['average_risk'], r['duration'] ))['id'] if eligible else None
