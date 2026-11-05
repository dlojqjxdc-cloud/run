"""QR RUN — Streamlit mobile running tracker.
Deploy app.py + requirements.txt on Streamlit Community Cloud (HTTPS).
QR code should contain the public deployed app URL, not the GitHub URL.
All running data stays in this browser's localStorage. No server database.
GPS and speech need an actual phone/browser test; background tracking is not guaranteed.
"""
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="QR RUN · 러닝 기록", page_icon="🏃", layout="centered")
st.markdown("""<style>.block-container{padding-top:1rem;padding-bottom:0}header{visibility:hidden}</style>""", unsafe_allow_html=True)
APP = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#edf3ff;font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif;font-size:15px}main{max-width:640px;margin:auto;padding:20px 16px}h1{font-size:30px;margin:8px 0}h2{font-size:19px}.sub,small{color:#a6b5cf;line-height:1.6}.tag{color:#9aefbe;font-size:12px;font-weight:800;letter-spacing:2px}.panel{background:#162237;border:1px solid #293951;border-radius:20px;padding:18px;margin:16px 0}.hero{text-align:center}.distance{font-size:64px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-3px}.unit{font-size:19px;color:#a6b5cf}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.metric{background:#0d182a;padding:14px;border-radius:13px;text-align:center}.value{font-size:25px;font-weight:750;font-variant-numeric:tabular-nums;margin-top:5px}button{border:0;border-radius:13px;padding:15px 12px;cursor:pointer;background:#293b57;color:white;font-size:16px;font-weight:750;touch-action:manipulation;width:100%;margin:5px 0}button.primary{background:#a4f2bf;color:#10231c}button.danger{background:#532b39;color:#ffc8d1}button:disabled{opacity:.35;cursor:default}label{display:flex;align-items:center;gap:10px;margin:12px 0;line-height:1.5}input[type=checkbox]{width:20px;height:20px;accent-color:#9aefbe}#status{line-height:1.6;overflow-wrap:anywhere;color:#c5d8f7}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:10px 4px;border-bottom:1px solid #293951}th{color:#a6b5cf}.record{padding:15px 0;border-bottom:1px solid #293951}.record button{width:auto;font-size:13px;padding:8px 14px}.notice{color:#ffdc9c;font-size:13px;line-height:1.7}details{margin-top:15px}summary{cursor:pointer;color:#a6b5cf}.empty{color:#a6b5cf;padding:14px 0}#toast{color:#9aefbe;line-height:1.6;min-height:24px}a{color:#a4f2bf}
</style></head><body><main>
<div class="tag">YOUR PACE, YOUR RUN</div><h1>🏃 QR RUN</h1><div class="sub">거리 · 시간 · 시속 · 페이스, 한눈에 확인하세요.</div>
<section class="panel hero"><h2>이번 러닝 전체 기록</h2><div class="grid"><div class="metric"><small>총 뛴 거리</small><div class="value"><span id="distance">0.00</span> <small>km</small></div></div><div class="metric"><small>총 운동 시간</small><div class="value" id="time">00:00:00</div></div><div class="metric"><small>평균 시속</small><div class="value"><span id="speed">0.0</span> <small>km/h</small></div></div><div class="metric"><small>평균 페이스</small><div class="value" id="pace">—</div><small>1km당 분:초</small></div></div></section>
<section class="panel"><h2>페이스가 얼마나 흔들렸나요?</h2><div class="grid"><div class="metric"><small>가장 빠른 시속</small><div class="value" id="fastest">—</div><small id="fastpace">페이스 —</small></div><div class="metric"><small>가장 느린 시속</small><div class="value" id="slowest">—</div><small id="slowpace">페이스 —</small></div></div><p id="variation" style="font-weight:750;line-height:1.8">10초 구간 2개가 쌓이면 속도·페이스 차이를 표시합니다.</p><small>최고·최저는 유효한 10초 구간 평균입니다. 정지 구간도 포함합니다. 차이가 클수록 속도 변화가 큽니다. GPS 수신 공백은 제외하며, GPS 오차가 반영될 수 있습니다.</small><div class="sub">GPS 정확도 <b id="accuracy">—</b></div></section>
<div class="grid"><button class="primary" id="start">▶ 시작</button><button class="danger" id="stop" disabled>■ 종료</button></div>
<button id="save" disabled>💾 이번 러닝 저장</button>
<section class="panel"><label><input type="checkbox" id="voice" checked>1km마다 천천히 음성 안내</label><button id="test">🔊 음성 테스트</button><div id="status" role="status">시작을 누르면 위치 권한을 요청합니다.</div><div id="toast" aria-live="polite"></div></section>
<div class="notice">정확한 측정을 위해 야외에서 사용하고, 휴대폰 화면을 켜두세요. 화면 잠금·백그라운드에서는 GPS와 음성이 중단될 수 있습니다. GPS 오차로 실제 거리와 차이가 날 수 있습니다.</div>
<section class="panel"><h2>1km 구간 기록</h2><div id="splits"></div></section>
<section class="panel"><h2>내 러닝 기록</h2><small>이 기기·이 브라우저에 저장됩니다. 브라우저 데이터 삭제, 시크릿 모드 종료, 앱 주소 변경 시 기록이 사라질 수 있습니다.</small><div id="records"></div></section>
<details><summary>사용 방법과 위치 권한 안내</summary><div class="sub"><p>① 시작 → 위치 허용 → GPS 수신 확인 → 달리기<br>② 종료 → 이번 러닝 저장<br>③ 저장 기록에서 개별 삭제</p><p>앱은 HTTPS 주소로 열어야 합니다. 카카오톡·네이버 등의 앱 내부 브라우저 대신 Safari 또는 Chrome으로 직접 여세요. 위치 권한은 브라우저와 휴대폰 설정에서 모두 허용해야 합니다.</p><p>위치가 차단되면 배포 사이트의 iframe 위치 권한 정책 때문일 수 있습니다. 브라우저가 위치 사용을 막는 배포 환경에서는 이 웹앱으로 우회할 수 없습니다.</p><p>시간 측정은 첫 유효 GPS 수신부터 시작합니다. 페이스는 경과 시간 ÷ GPS 이동 거리이며, 정지 시간도 포함합니다. 정확도 35m 초과, 3m 미만 이동, 시속 43.2km 초과 점프는 걸러냅니다. 실제 이동 일부도 제외될 수 있어 전문 운동기기와 일치하지 않을 수 있습니다.</p><p>주행 중에는 새로고침하거나 페이지를 닫지 마세요. 저장 전 러닝은 보존되지 않습니다. 저장 기록은 서버에 전송하지 않습니다.</p></div></details>
</main><script>
'use strict';
const $=id=>document.getElementById(id);
const KEY='qr_run_records_v1';
let records=[],storageOK=true,watchId=null,running=false,pending=false,startAt=0,endAt=0,total=0,last=null,splits=[],lastSplitTime=0,saved=false,wakeLock=null, speedStats={count:0,min:null,max:null}, speedAnchor=null;
try{const raw=JSON.parse(localStorage.getItem(KEY)||'[]');if(!Array.isArray(raw))throw Error('invalid');records=raw.filter(r=>r&&typeof r.id==='string'&&Number.isFinite(r.distance)&&Number.isFinite(r.seconds)&&Number.isFinite(r.date));const probe=KEY+'_probe';localStorage.setItem(probe,'1');localStorage.removeItem(probe);}catch(e){storageOK=false;$('toast').textContent='브라우저 저장 공간에 접근할 수 없거나 기존 데이터가 손상되었습니다. 기록 저장은 사용할 수 없습니다.';}
function duration(s){s=Math.max(0,Math.floor(s));return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(v=>String(v).padStart(2,'0')).join(':');}
function pace(s){if(!Number.isFinite(s)||s<=0)return '—';let n=Math.round(s);return Math.floor(n/60)+':'+String(n%60).padStart(2,'0');}
// Fixed, non-overlapping 10-second distance windows; interpolate boundaries.
function sampleSpeed(t, distance){
 if(!speedAnchor){speedAnchor={t,distance,end:t+10000,base:distance};return;}
 if(t<=speedAnchor.t)return;
 if(t-speedAnchor.t>20000){speedAnchor={t,distance,end:t+10000,base:distance};return;}
 const prevT=speedAnchor.t,prevD=speedAnchor.distance;
 while(t>=speedAnchor.end){
  const boundaryD=prevD+(distance-prevD)*(speedAnchor.end-prevT)/(t-prevT);
  const speed=Math.max(0,(boundaryD-speedAnchor.base)*0.36);
  speedStats.count++;
  speedStats.min=speedStats.min===null?speed:Math.min(speedStats.min,speed);
  speedStats.max=speedStats.max===null?speed:Math.max(speedStats.max,speed);
  speedAnchor.base=boundaryD;speedAnchor.end+=10000;
 }
 speedAnchor.t=t;speedAnchor.distance=distance;
}
function speedPace(speed){return speed>0?'페이스 '+pace(3600/speed)+' /km':'정지 · 페이스 계산 불가';}
function variationText(stats){
 if(!stats||stats.count<2)return '10초 구간 2개가 쌓이면 속도·페이스 차이를 표시합니다.';
 const spread=(stats.max-stats.min).toFixed(1);
 if(stats.min<=0)return `속도 차이 ${spread} km/h · 정지 구간 포함으로 페이스 차이는 계산하지 않습니다. (${stats.count}개 구간)`;
 const diff=Math.max(0,Math.round(3600/stats.min-3600/stats.max));
 return `속도 차이 ${spread} km/h · 페이스 차이 ${Math.floor(diff/60)}분 ${diff%60}초 /km (${stats.count}개 구간)`;
}
function updateVariation(){
 const ready=speedStats.count>0;
 $('fastest').textContent=ready?speedStats.max.toFixed(1)+' km/h':'—';
 $('slowest').textContent=ready?speedStats.min.toFixed(1)+' km/h':'—';
 $('fastpace').textContent=ready?speedPace(speedStats.max):'페이스 —';
 $('slowpace').textContent=ready?speedPace(speedStats.min):'페이스 —';
 $('variation').textContent=variationText(speedStats);
}
function elapsed(){return startAt?((running?Date.now():endAt)-startAt)/1000:0;}
function update(){updateVariation();const sec=elapsed(),km=total/1000;$('distance').textContent=km.toFixed(2);$('time').textContent=duration(sec);$('pace').textContent=km>0?pace(sec/km):'—';$('speed').textContent=sec>0?(km/(sec/3600)).toFixed(1):'0.0';$('start').disabled=running||pending;$('stop').disabled=!running&&!pending;$('save').disabled=running||pending||!startAt||!total||saved||!storageOK;}
function speak(text){if(!('speechSynthesis' in window)){$('toast').textContent='이 브라우저는 음성 안내를 지원하지 않습니다.';return;}const u=new SpeechSynthesisUtterance(text);u.lang='ko-KR';u.rate=0.78;u.pitch=1;const voices=speechSynthesis.getVoices();const ko=voices.find(v=>v.lang.toLowerCase().startsWith('ko'));if(ko)u.voice=ko;u.onerror=()=>{$('toast').textContent='음성 재생이 제한되었습니다. 화면의 구간 기록을 확인하세요.';};speechSynthesis.speak(u);}
$('test').onclick=()=>speak('음성 안내입니다. 1킬로미터 완료. 이번 구간 페이스, 6분 30초. 시속, 9점 2킬로미터입니다.');
function haversine(a,b){const r=Math.PI/180,dLat=(b.latitude-a.latitude)*r,dLon=(b.longitude-a.longitude)*r;const h=Math.sin(dLat/2)**2+Math.cos(a.latitude*r)*Math.cos(b.latitude*r)*Math.sin(dLon/2)**2;return 6371000*2*Math.asin(Math.sqrt(Math.min(1,h)));}
async function lock(){try{if('wakeLock' in navigator)wakeLock=await navigator.wakeLock.request('screen');}catch(e){/* Optional; unsupported browsers still run. */}}
function unlock(){if(wakeLock){wakeLock.release().catch(()=>{});wakeLock=null;}}
function renderSplits(){const node=$('splits');node.replaceChildren();if(!splits.length){node.textContent='1km를 달리면 구간별 페이스와 속도가 표시됩니다.';node.className='empty';return;}node.className='';const table=document.createElement('table');const header=document.createElement('tr');for(const text of ['구간','구간 페이스','구간 속도']){const th=document.createElement('th');th.textContent=text;header.append(th);}table.append(header);for(const s of splits){const tr=document.createElement('tr');for(const text of [s.km+' km',pace(s.seconds)+' /km',s.speed.toFixed(1)+' km/h']){const td=document.createElement('td');td.textContent=text;tr.append(td);}table.append(tr);}node.append(table);}
function position(pos){if(!running&&!pending)return;const c=pos.coords;$('accuracy').textContent=Number.isFinite(c.accuracy)?'±'+Math.round(c.accuracy)+'m':'—';if(!Number.isFinite(c.latitude)||!Number.isFinite(c.longitude)||!Number.isFinite(c.accuracy)||c.accuracy>35){speedAnchor=null;$('status').textContent='GPS 정확도가 낮습니다. 하늘이 잘 보이는 곳에서 기다려 주세요. 해당 위치는 거리에 반영하지 않습니다.';return;}
const now=Date.now();const p={latitude:c.latitude,longitude:c.longitude,timestamp:pos.timestamp};
if(pending){sampleSpeed(p.timestamp,0);pending=false;running=true;startAt=now;lastSplitTime=0;last=p;$('status').textContent='🟢 GPS 연결 완료. 거리와 시간 측정을 시작했습니다.';if($('voice').checked)speak('측정을 시작합니다. 안전하게 달리세요.');lock();update();return;}
const gap=(p.timestamp-last.timestamp)/1000;if(gap<=0)return;
if(gap>20){speedAnchor=null;sampleSpeed(p.timestamp,total);last=p;$('status').textContent='GPS 수신 공백이 감지되었습니다. 누락된 구간은 추정하지 않고 현재 위치에서 측정을 이어갑니다.';return;}
const d=haversine(last,p);if(d/gap>12){speedAnchor=null;last=p;$('status').textContent='비정상적인 GPS 위치 이동을 제외했습니다.';return;}
if(d<3){sampleSpeed(p.timestamp,total);update();return;}
const old=total;const previousSec=Math.max(0,(last.timestamp-startAt)/1000);const currentSec=Math.max(previousSec,(p.timestamp-startAt)/1000);total+=d;sampleSpeed(p.timestamp,total);
while(total>=(splits.length+1)*1000){const km=splits.length+1;const ratio=(km*1000-old)/d;const crossing=previousSec+(currentSec-previousSec)*ratio;const seconds=Math.max(.001,crossing-lastSplitTime);lastSplitTime=crossing;const speed=3600/seconds;splits.push({km,seconds,speed});if($('voice').checked){const n=Math.round(seconds),speedText=speed.toFixed(1).replace('.','점 ');speak(`${km}킬로미터 완료. 이번 1킬로미터 구간 페이스, ${Math.floor(n/60)}분 ${n%60}초. 시속, ${speedText}킬로미터입니다.`);}renderSplits();}
last=p;$('status').textContent='🟢 측정 중 · 1km마다 구간 페이스와 속도를 알려드립니다.';update();}
function geoError(error){if(!pending&&!running)return;const reason={1:'위치 권한이 거부되었거나 배포 환경의 위치 권한 정책으로 차단되었습니다. Chrome/Safari에서 주소를 직접 열고 위치 권한을 확인하세요.',2:'현재 위치를 찾을 수 없습니다. 휴대폰 위치 설정과 야외 수신 상태를 확인하세요.',3:'GPS 수신 시간이 초과되었습니다. 야외에서 잠시 기다려 주세요.'};$('status').textContent=reason[error.code]||'GPS 오류가 발생했습니다.';if(error.code===1){stop(false);} }
$('start').onclick=()=>{if(!navigator.geolocation){$('status').textContent='이 브라우저는 GPS 위치 측정을 지원하지 않습니다.';return;}if(!window.isSecureContext){$('status').textContent='GPS 사용에는 HTTPS 주소가 필요합니다.';return;}if(startAt&&!saved&&!confirm('저장하지 않은 이번 기록을 버리고 새 러닝을 시작할까요?'))return;
if('speechSynthesis' in window)speechSynthesis.cancel();startAt=0;endAt=0;total=0;last=null;splits=[];lastSplitTime=0;saved=false;speedStats={count:0,min:null,max:null};speedAnchor=null;pending=true;renderSplits();$('toast').textContent='';$('status').textContent='위치 권한을 허용해 주세요. 정확한 GPS 위치를 기다리는 중입니다…';update();if($('voice').checked)speak('위치를 확인하고 있습니다.');try{watchId=navigator.geolocation.watchPosition(position,geoError,{enableHighAccuracy:true,maximumAge:0,timeout:20000});}catch(e){pending=false;$('status').textContent='위치 측정을 시작하지 못했습니다. 브라우저 권한과 배포 환경을 확인하세요.';update();}};
function stop(announce=true){if(watchId!==null){navigator.geolocation.clearWatch(watchId);watchId=null;}endAt=Date.now();running=false;pending=false;unlock();if(announce){$('status').textContent=startAt?'측정을 종료했습니다. 이번 러닝 저장 버튼을 눌러 보관하세요.':'GPS 수신 대기를 취소했습니다.';if(startAt&&$('voice').checked)speak('측정을 종료했습니다. 기록을 저장해 주세요.');}update();}
$('stop').onclick=()=>stop();
function persist(next){try{localStorage.setItem(KEY,JSON.stringify(next));records=next;return true;}catch(e){$('toast').textContent='저장 공간 부족 또는 브라우저 제한으로 저장/삭제에 실패했습니다.';return false;}}
$('save').onclick=()=>{if(!startAt||total<=0||running||pending||saved)return;const r={id:Date.now().toString(36)+'-'+Math.random().toString(36).slice(2),date:startAt,distance:total,seconds:elapsed(),speedStats:{...speedStats},splits:splits.map(s=>({...s}))};if(persist([r,...records])){saved=true;$('toast').textContent='이번 러닝을 브라우저에 저장했습니다.';renderRecords();update();}};
function renderRecords(){const node=$('records');node.replaceChildren();if(!records.length){node.textContent='아직 저장한 기록이 없습니다.';node.className='empty';return;}node.className='';records.forEach(r=>{const box=document.createElement('div');box.className='record';const date=document.createElement('strong');date.textContent=new Date(r.date).toLocaleString('ko-KR');const info=document.createElement('p');const km=r.distance/1000;info.textContent=`${km.toFixed(2)} km · ${duration(r.seconds)} · 평균 ${pace(r.seconds/km)} /km · ${r.seconds>0?(km/(r.seconds/3600)).toFixed(1):'0.0'} km/h`;box.append(date,info);const stats=r.speedStats;if(stats&&stats.count>0&&Number.isFinite(stats.min)&&Number.isFinite(stats.max)){const variation=document.createElement('p');variation.className='sub';variation.textContent=`10초 구간 기준 · 최고 ${stats.max.toFixed(1)} km/h (${speedPace(stats.max)}) · 최저 ${stats.min.toFixed(1)} km/h (${speedPace(stats.min)}) · ${variationText(stats)}`;box.append(variation);}else{const legacy=document.createElement('small');legacy.textContent='최고·최저 시속 정보 없음 (기존 기록 또는 10초 미만 러닝)';box.append(legacy);}if(Array.isArray(r.splits)&&r.splits.length){const detail=document.createElement('div');detail.className='sub';detail.textContent=r.splits.map(s=>`${s.km}km: ${pace(s.seconds)} /km, ${Number(s.speed).toFixed(1)} km/h`).join(' · ');box.append(detail);}const del=document.createElement('button');del.className='danger';del.textContent='이 기록 삭제';del.onclick=()=>{if(confirm('이 기록을 영구 삭제할까요?')&&persist(records.filter(x=>x.id!==r.id))){renderRecords();$('toast').textContent='기록을 삭제했습니다.';}};box.append(del);node.append(box);});}
window.addEventListener('beforeunload',e=>{if(running||pending||(startAt&&!saved&&total>0)){e.preventDefault();e.returnValue='';}});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&running){lock();$('status').textContent='앱으로 돌아왔습니다. 백그라운드 동안 위치가 누락되었을 수 있습니다.';}});
setInterval(update,250);renderSplits();renderRecords();update();
// Resize this Streamlit component as history grows, without an external JS dependency.
function resize(){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:document.documentElement.scrollHeight},'*');}
new ResizeObserver(resize).observe(document.body);resize();
</script></body></html>'''
components.html(APP, height=1450, scrolling=True)
