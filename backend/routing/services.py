import math
import hashlib
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import httpx
from django.core.cache import cache
from .risk import classify, summarize, recommend
MILE = 1609.344

class ProviderError(Exception):
    pass

def fetch(url, params=None):
    key = hashlib.sha256((url + str(params)).encode()).hexdigest()
    found = cache.get(key)
    if found is not None:
        return found
    try:
        response = httpx.get(url, params=params, timeout=35, headers={'User-Agent':'WeatherHaul/1.0 (route-planning prototype)'})
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError('A routing or weather provider is unavailable. Please retry.') from exc
    cache.set(key, data)
    return data

def geocode(query):
    result = fetch('https://geocoding-api.open-meteo.com/v1/search', {'name':query, 'count':1, 'language':'en', 'format':'json'})
    if not result.get('results'):
        raise ValueError('Location not found: ' + query)
    r = result['results'][0]
    return {'name': ', '.join(filter(None,[r['name'],r.get('admin1')])), 'lat':r['latitude'], 'lng':r['longitude']}

def routing(a, b):
    def get(via=None):
        points = [a] + ([via] if via else []) + [b]
        coords = ';'.join(f"{p['lng']},{p['lat']}" for p in points)
        response = fetch('https://router.project-osrm.org/route/v1/driving/' + coords, {'alternatives':'3' if not via else 'false', 'overview':'full', 'geometries':'geojson', 'annotations':'distance,duration', 'steps':'false'})
        if response.get('code') != 'Ok':
            raise ProviderError('No drivable route found between these locations.')
        return response['routes']
    routes = get()
    # Public OSRM can return fewer alternatives. Request additional real routes via corridor offsets.
    if len(routes) < 3:
        for offset in (.45, -.45, .8, -.8):
            via = {'lat':(a['lat']+b['lat'])/2 + offset, 'lng':(a['lng']+b['lng'])/2}
            try:
                extra = get(via)[0]
                if all(abs(extra['distance']-r['distance']) > 1609 for r in routes):
                    routes.append(extra)
            except ProviderError:
                continue
            if len(routes) >= 3:
                break
    return routes[:3]

def sample_route(route, spacing):
    coords = route['geometry']['coordinates']
    distances, durations = [], []
    for leg in route['legs']:
        distances.extend(leg['annotation']['distance'])
        durations.extend(leg['annotation']['duration'])
    if len(distances) != len(coords)-1:
        raise ProviderError('Routing geometry and segment annotations do not match.')
    # Include OSRM turn penalties while retaining segment-specific speed differences.
    annotated_duration = sum(durations)
    if annotated_duration > 0:
        durations = [s * route['duration'] / annotated_duration for s in durations]
    total = sum(distances)
    if total <= 0:
        raise ValueError('Origin and destination must be different.')
    targets = [i * spacing * MILE for i in range(math.floor(total / (spacing*MILE))+1)]
    if total-targets[-1] > .01:
        targets.append(total)
    checkpoints, segment, traveled, elapsed = [], 0, 0, 0
    for target in targets:
        while segment < len(distances)-1 and traveled+distances[segment] < target:
            traveled += distances[segment]
            elapsed += durations[segment]
            segment += 1
        fraction = (target-traveled)/distances[segment] if distances[segment] else 0
        a,b = coords[segment:segment+2]
        checkpoints.append({'lng':a[0]+(b[0]-a[0])*fraction,'lat':a[1]+(b[1]-a[1])*fraction,'mile':target/MILE,'seconds':elapsed+durations[segment]*fraction})
    return checkpoints

def weather(points):
    def batch(chunk):
        data = fetch('https://api.open-meteo.com/v1/forecast', {'latitude':','.join(str(round(p['lat'],4)) for p in chunk), 'longitude':','.join(str(round(p['lng'],4)) for p in chunk), 'hourly':'wind_speed_10m,rain,showers,snowfall,temperature_2m', 'wind_speed_unit':'mph','temperature_unit':'fahrenheit','precipitation_unit':'inch','timezone':'GMT','forecast_days':7})
        return data if isinstance(data,list) else [data]
    chunks = [points[i:i+35] for i in range(0,len(points),35)]
    with ThreadPoolExecutor(max_workers=3) as executor:
        forecasts = [f for group in executor.map(batch,chunks) for f in group]
    if len(forecasts) != len(points):
        raise ProviderError('Weather provider returned incomplete locations.')
    return forecasts

def at_time(forecast, arrival, load):
    arrival = arrival.astimezone(timezone.utc)
    h = forecast['hourly']
    # Open-Meteo hourly rain/snow represent preceding-hour totals; ceil ETA to that interval.
    hour = arrival.replace(minute=0,second=0,microsecond=0)
    if arrival > hour:
        hour += timedelta(hours=1)
    key = hour.strftime('%Y-%m-%dT%H:%M')
    try:
        i = h['time'].index(key)
        values = [h[k][i] for k in ('wind_speed_10m','rain','showers','snowfall','temperature_2m')]
        if any(x is None or not math.isfinite(x) for x in values):
            raise ValueError()
    except (ValueError, KeyError, IndexError):
        raise ProviderError('Arrival is outside the available forecast or weather data is missing.')
    wind,rain,showers,snow,temp = values
    units = forecast.get('hourly_units', {})
    snow_unit = units.get('snowfall')
    if snow_unit == 'cm':
        snow /= 2.54
    elif snow_unit != 'inch':
        raise ProviderError('Weather provider returned an unsupported snowfall unit.')
    if units.get('rain') != 'inch' or units.get('showers') != 'inch' or units.get('wind_speed_10m') not in ('mp/h', 'mph'):
        raise ProviderError('Weather provider returned unsupported rain or wind units.')
    return {'wind':wind,'rain':rain+showers,'snow':snow,'temperature':temp,'risk':classify(wind,rain+showers,snow,load),'forecast_time':key+'Z'}

def plan_trip(origin, destination, departure, load, spacing):
    with ThreadPoolExecutor(max_workers=2) as executor:
        a,b = list(executor.map(geocode,[origin,destination]))
    candidates = routing(a,b)
    routes, points = [], []
    for i,r in enumerate(candidates):
        cps = sample_route(r,spacing)
        if len(cps) > 220:
            raise ValueError('Trip is too long for this checkpoint spacing. Choose a wider spacing.')
        route = {'id':f'route-{i+1}','name':f'Route {i+1}','via': 'Direct corridor' if i==0 else 'Alternative corridor','geometry':r['geometry']['coordinates'],'distance':r['distance']/MILE,'duration':r['duration'],'checkpoints':cps}
        routes.append(route)
        points.extend(cps)
    # Corridor lattice, bounded for reliable response size and heat rendering.
    lngs=[p['lng'] for p in points]; lats=[p['lat'] for p in points]
    grid = [{'lat':min(lats)+(max(lats)-min(lats))*y/5,'lng':min(lngs)+(max(lngs)-min(lngs))*x/9} for y in range(6) for x in range(10)]
    forecasts = weather(points+grid)
    for p, forecast in zip(points,forecasts):
        arrival = departure+timedelta(seconds=p['seconds'])
        p.update(at_time(forecast,arrival,load))
        p['eta'] = arrival.isoformat()
    for r in routes:
        r.update(summarize(r['checkpoints']))
        r['arrival'] = (departure+timedelta(seconds=r['duration'])).isoformat()
    corridor=[]
    for p,f in zip(grid,forecasts[len(points):]):
        p['forecast']=[at_time(f,departure+timedelta(hours=h),load) for h in range(49)]
        corridor.append(p)
    return {'mode':'live','origin':a,'destination':b,'departure':departure.isoformat(),'load':load,'spacing':spacing,'routes':routes,'recommended':recommend(routes),'corridor':corridor,'generated_at':datetime.now(timezone.utc).isoformat(),'warnings':(['Only '+str(len(routes))+' distinct routes were returned by the provider.'] if len(routes)<3 else [])+['OSRM driving routes do not validate truck height, axle limits, hazmat or road closures. ETAs exclude rest breaks and traffic.']}
