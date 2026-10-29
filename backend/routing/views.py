import json, math
from datetime import datetime, timezone, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from .services import plan_trip, ProviderError

@require_GET
def health(request):
    return JsonResponse({'status':'ok','service':'weatherhaul-django'})

@csrf_exempt
@require_POST
def plan(request):
    if len(request.body) > 4096:
        return JsonResponse({'error':'Request too large.'},status=413)
    try:
        data=json.loads(request.body)
        if not isinstance(data,dict):
            raise ValueError('Expected a JSON object.')
        origin,destination = str(data.get('origin','')).strip(),str(data.get('destination','')).strip()
        if not origin or not destination or max(len(origin),len(destination)) > 150:
            raise ValueError('Enter an origin and destination, each under 150 characters.')
        load = float(data.get('load',0))
        if not math.isfinite(load) or not 0 <= load <= 100000:
            raise ValueError('Load must be between 0 and 100,000 lb.')
        spacing = data.get('spacing',25)
        if spacing not in (10,25,50):
            raise ValueError('Checkpoint spacing must be 10, 25 or 50 miles.')
        departure = datetime.fromisoformat(str(data.get('departure','')).replace('Z','+00:00'))
        if departure.tzinfo is None:
            raise ValueError('Departure must include a timezone offset.')
        now = datetime.now(timezone.utc)
        if departure < now-timedelta(minutes=5) or departure > now+timedelta(hours=96):
            raise ValueError('Choose a departure between now and 96 hours from now.')
        return JsonResponse(plan_trip(origin,destination,departure,load,spacing))
    except (ValueError,TypeError,OverflowError,json.JSONDecodeError) as exc:
        return JsonResponse({'error':str(exc)},status=400)
    except ProviderError as exc:
        return JsonResponse({'error':str(exc)},status=502)
