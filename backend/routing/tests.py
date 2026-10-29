import json, math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from django.test import SimpleTestCase
from .risk import classify, summarize, recommend
from .services import sample_route, at_time, ProviderError

class RiskTests(SimpleTestCase):
    def test_wind_and_load_boundaries(self):
        for wind,load,expected in [(24.99,45000,0),(25,0,1),(34.99,45000,1),(35,40000,2),(35,40001,3),(44.99,40001,3),(45,30000,3),(45,30001,4),(54.99,0,3),(55,0,4)]:
            with self.subTest(wind=wind,load=load):self.assertEqual(classify(wind,0,0,load),expected)
    def test_precipitation_boundaries(self):
        for rain,risk in [(.099,0),(.1,1),(.25,2),(.5,3),(1,3),(1.001,4)]:self.assertEqual(classify(0,rain,0,0),risk)
        for snow,risk in [(.49,0),(.5,1),(1,2),(2,3),(3,3),(3.01,4)]:self.assertEqual(classify(0,0,snow,0),risk)
    def test_missing_and_nonfinite_are_never_low(self):
        for value in [float('nan'),float('inf'),-1]:
            with self.assertRaises(ValueError):classify(value,0,0,0)
    def test_conservative_segment_and_weighting(self):
        result=summarize([{'mile':0,'risk':0},{'mile':10,'risk':1},{'mile':25,'risk':2}])
        self.assertEqual(result['risk_miles'],[0,10,15,0,0]);self.assertEqual(result['average_risk'],1.6)
    def test_recommendation_order_and_exclusion(self):
        def r(id,sev,high,avg,dur,eligible=True):return dict(id=id,risk_miles=[0,0,high,sev,0],average_risk=avg,duration=dur,eligible=eligible)
        self.assertEqual(recommend([r('fast',1,0,0,1),r('safe',0,10,2,20)]),'safe')
        self.assertEqual(recommend([r('high',0,10,0,1),r('low',0,1,2,20)]),'low')
        self.assertEqual(recommend([r('a',0,0,1,100),r('b',0,0,2,1)]),'a')
        self.assertEqual(recommend([r('a',0,0,1,100),r('b',0,0,1,50)]),'b')
        self.assertIsNone(recommend([r('blocked',0,0,0,1,False)]))

class SamplingTests(SimpleTestCase):
    def test_sampling_uses_segment_durations_and_includes_destination(self):
        r={'duration':1000,'geometry':{'coordinates':[[0,0],[1,0],[2,0]]},'legs':[{'annotation':{'distance':[16093.44,16093.44],'duration':[100,900]}}]}
        cps=sample_route(r,10)
        self.assertEqual(len(cps),3);self.assertAlmostEqual(cps[1]['seconds'],100);self.assertAlmostEqual(cps[-1]['seconds'],1000)
        self.assertAlmostEqual(cps[-1]['mile'],20);self.assertAlmostEqual(cps[-1]['lng'],2)
        r['duration']=1100
        self.assertAlmostEqual(sample_route(r,10)[-1]['seconds'],1100)
    def test_forecast_interval_units_and_rain_showers(self):
        f={'hourly_units':{'wind_speed_10m':'mp/h','rain':'inch','showers':'inch','snowfall':'cm'},'hourly':{'time':['2026-10-29T01:00'],'wind_speed_10m':[20],'rain':[.1],'showers':[.2],'snowfall':[2.54],'temperature_2m':[40]}}
        w=at_time(f,datetime(2026,10,29,0,15,tzinfo=timezone.utc),32000)
        offset=timezone(timedelta(hours=5,minutes=30))
        self.assertEqual(at_time(f,datetime(2026,10,29,5,45,tzinfo=offset),32000),w)
        self.assertAlmostEqual(w['rain'],.3);self.assertEqual(w['snow'],1);self.assertEqual(w['risk'],2)
        with self.assertRaises(ProviderError):at_time(f,datetime(2026,10,30,tzinfo=timezone.utc),0)
        f['hourly_units']['snowfall']='inch'
        f['hourly']['snowfall'][0]=1
        self.assertEqual(at_time(f,datetime(2026,10,29,1,tzinfo=timezone.utc),0)['snow'],1)
        f['hourly']['rain'][0]=None
        with self.assertRaises(ProviderError):at_time(f,datetime(2026,10,29,1,tzinfo=timezone.utc),0)

class ApiTests(SimpleTestCase):
    def post(self,data):return self.client.post('/api/plan',data=json.dumps(data),content_type='application/json')
    def valid(self):return dict(origin='Denver',destination='Kansas City',load=32000,spacing=25,departure=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())
    def test_health(self):self.assertEqual(self.client.get('/api/health').status_code,200)
    def test_validation(self):
        for key,value in [('load',-1),('load','nan'),('spacing',12),('origin',''),('departure','tomorrow'),('departure','2026-10-29T12:00')]:
            data=self.valid();data[key]=value;self.assertEqual(self.post(data).status_code,400)
        self.assertEqual(self.post([]).status_code,400)
    @patch('routing.views.plan_trip')
    def test_provider_errors_visible(self,plan):
        plan.side_effect=ProviderError('Weather unavailable')
        self.assertEqual(self.post(self.valid()).status_code,502)
    @patch('routing.views.plan_trip')
    def test_valid_plan(self,plan):
        plan.return_value={'mode':'live','routes':[],'recommended':None}
        self.assertEqual(self.post(self.valid()).json()['mode'],'live')
        self.assertEqual(plan.call_args.args[-1],25)
