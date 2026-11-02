import {test} from 'node:test';
import assert from 'node:assert/strict';
import {locateOrigin} from '../src/location.js';
const args = () => ({onStage:()=>{},signal:new AbortController().signal,fetchEstimate:async()=>({latitude:0,longitude:0})});
test('GPS wins and uses the requested options', async()=>{
 const p=await locateOrigin({...args(),fetchEstimate:()=>assert.fail('IP was called'),geolocation:{getCurrentPosition(ok,fail,options){
  assert.equal(options.timeout,10000);assert.equal(options.enableHighAccuracy,true);ok({coords:{latitude:-33,longitude:151}});
 }}});assert.equal(p.method,'gps');assert.equal(p.lat,-33);
});
for(const code of [1,2,3]) test('IP fallback on geolocation error '+code,async()=>{
 const stages=[];const p=await locateOrigin({...args(),onStage:(s)=>stages.push(s),geolocation:{getCurrentPosition:(ok,fail)=>fail({code})}});
 assert.deepEqual(stages,['gps','ip']);assert.equal(p.method,'ip');assert.equal(p.lon,0);
});
test('invalid IP data is rejected', async()=>assert.rejects(locateOrigin({...args(),fetchEstimate:async()=>({latitude:null,longitude:0})})));
test('cancelled GPS cannot overwrite manual origin or call IP',async()=>{
 const c=new AbortController();let finish;
 const result=locateOrigin({...args(),signal:c.signal,geolocation:{getCurrentPosition:ok=>{finish=ok}},fetchEstimate:()=>assert.fail()});
 c.abort();finish({coords:{latitude:1,longitude:2}});await assert.rejects(result);
});
