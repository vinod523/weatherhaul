import {test} from 'node:test';
import assert from 'node:assert/strict';
import {classify,summarize,recommend} from './risk.js';
test('wind and strict load boundaries',()=>{for(const [w,l,r] of [[24.99,45000,0],[25,0,1],[35,40000,2],[35,40001,3],[45,30000,3],[45,30001,4],[55,0,4]]) assert.equal(classify(w,0,0,l),r)});
test('precipitation shared endpoints are conservative',()=>{for(const [rain,r] of [[.099,0],[.1,1],[.25,2],[.5,3],[1,3],[1.001,4]]) assert.equal(classify(0,rain,0,0),r); for(const [s,r] of [[.49,0],[.5,1],[1,2],[2,3],[3,3],[3.01,4]]) assert.equal(classify(0,0,s,0),r)});
test('distance weighting and no travel veto',()=>{const s=summarize([{mile:0,risk:0},{mile:10,risk:3},{mile:25,risk:0}]);assert.deepEqual(s.risk_miles,[0,0,0,25,0]);assert.equal(s.average_risk,3);assert.equal(recommend([{id:'bad',eligible:false,risk_miles:[0,0,0,0,1],average_risk:4,duration:10}]),null)});
test('lexicographic recommendation',()=>{const route=(id,severe,high,avg,time)=>({id,eligible:true,risk_miles:[0,0,high,severe,0],average_risk:avg,duration:time});assert.equal(recommend([route('fast',1,0,0,1),route('safe',0,5,1,10)]),'safe'); assert.equal(recommend([route('a',0,1,1,10),route('b',0,1,1,5)]),'b')});
