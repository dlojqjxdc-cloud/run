"""QR RUN — Streamlit mobile running tracker.
Deploy app.py + requirements.txt on Streamlit Community Cloud (HTTPS).
QR code should contain the public deployed app URL, not the GitHub URL.
Google sign-in via Firebase Authentication; records in Firestore users/{uid}/runs.
Firebase initial configuration and account-scoped security rules are REQUIRED.
Legacy browser records can be explicitly imported. Completed runs auto-save.
Closing mid-run still loses the in-memory active run; cloud save must finish first.
GPS and speech need an actual phone/browser test; background tracking is not guaranteed.
"""
import json
import tempfile
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="QR RUN · 러닝 기록", page_icon="🏃", layout="centered")
st.markdown("""<style>.block-container{padding-top:1rem;padding-bottom:0}header{visibility:hidden}</style>""", unsafe_allow_html=True)

# Firebase WEB configuration is public client configuration, NOT a service-account key.
# Put it in Streamlit app settings -> Secrets, not in the GitHub repository.
try:
    firebase_config = dict(st.secrets["firebase"])
except Exception:
    firebase_config = {}
required = ("apiKey", "authDomain", "projectId", "appId")
if not all(isinstance(firebase_config.get(k), str) and firebase_config[k].strip() for k in required):
    st.title("🏃 QR RUN · 구글 로그인 연결")
    st.info("Firebase를 연결하면 구글 계정별로 러닝 기록을 저장합니다. 아래 설정을 먼저 완료해 주세요.")
    st.markdown("""### 최초 1회 설정
1. Firebase Console에서 프로젝트와 **웹 앱**을 만듭니다.
2. **Authentication → Sign-in method → Google**을 사용 설정하고 지원 이메일을 지정합니다.
3. **Authentication → Settings → Authorized domains**에 실제 Streamlit 앱 도메인을 추가합니다. `https://`와 경로는 제외합니다.
4. **Firestore Database**를 **프로덕션 모드**, 기본 데이터베이스 **(default)**로 생성합니다. 아래 규칙을 게시합니다.
5. 웹 앱 설정의 `firebaseConfig` 값을 Streamlit **Settings → Secrets**에 다음 TOML 형식으로 넣고 앱을 재시작합니다.

서비스 계정 JSON이나 구글 비밀번호는 필요하지 않습니다. 브라우저에 전달되는 웹 설정값만 사용합니다.
""")
    st.code('''[firebase]
apiKey = "웹 앱 설정의 apiKey"
authDomain = "프로젝트ID.firebaseapp.com"
projectId = "실제 프로젝트ID"
appId = "웹 앱 설정의 appId"
''', language="toml")
    st.markdown("### Firestore 보안 규칙 · 전체 교체 후 게시")
    st.code('''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/runs/{runId} {
      allow read, write: if request.auth != null
        && request.auth.uid == userId;
    }
  }
}''', language="text")
    st.warning("테스트 모드의 전체 공개 규칙을 사용하지 마세요. 기존 allow-all 규칙이 남아 있으면 계정별 접근 제한이 무효화됩니다.")
    st.markdown("앱은 HTTPS의 Chrome/Safari에서 직접 열고 팝업을 허용하세요. Streamlit 내장 프레임 환경과 모바일 브라우저 정책에 따라 구글 팝업 로그인이 제한될 수 있으므로 배포 도메인에서 실기기 테스트가 필요합니다.")
    st.stop()

APP = r'''<!DOCTYPE html>

<html lang="ko"><head><meta charset="utf-8"/><meta content="width=device-width,initial-scale=1" name="viewport"/>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#edf3ff;font-family:system-ui,-apple-system,'Malgun Gothic',sans-serif;font-size:15px}main{max-width:640px;margin:auto;padding:20px 16px}h1{font-size:30px;margin:8px 0}h2{font-size:19px}.sub,small{color:#a6b5cf;line-height:1.6}.tag{color:#9aefbe;font-size:12px;font-weight:800;letter-spacing:2px}.panel{background:#162237;border:1px solid #293951;border-radius:20px;padding:18px;margin:16px 0}.hero{text-align:center}.distance{font-size:64px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-3px}.unit{font-size:19px;color:#a6b5cf}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.metric{background:#0d182a;padding:14px;border-radius:13px;text-align:center}.value{font-size:25px;font-weight:750;font-variant-numeric:tabular-nums;margin-top:5px}button{border:0;border-radius:13px;padding:15px 12px;cursor:pointer;background:#293b57;color:white;font-size:16px;font-weight:750;touch-action:manipulation;width:100%;margin:5px 0}button.primary{background:#a4f2bf;color:#10231c}button.danger{background:#532b39;color:#ffc8d1}button:disabled{opacity:.35;cursor:default}label{display:flex;align-items:center;gap:10px;margin:12px 0;line-height:1.5}input[type=checkbox]{width:20px;height:20px;accent-color:#9aefbe}#status{line-height:1.6;overflow-wrap:anywhere;color:#c5d8f7}table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:10px 4px;border-bottom:1px solid #293951}th{color:#a6b5cf}.record{padding:15px 0;border-bottom:1px solid #293951}.record button{width:auto;font-size:13px;padding:8px 14px}.notice{color:#ffdc9c;font-size:13px;line-height:1.7}details{margin-top:15px}summary{cursor:pointer;color:#a6b5cf}.empty{color:#a6b5cf;padding:14px 0}#toast{color:#9aefbe;line-height:1.6;min-height:24px}a{color:#a4f2bf}

[hidden]{display:none!important}
main{padding:10px 12px 16px;max-width:600px}body{font-size:14px}
.app-header{display:flex;justify-content:space-between;align-items:center;padding:4px 2px 10px}.app-header strong{font-size:21px}.app-header span{color:#a6b5cf;font-size:12px}
.view-nav{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;position:sticky;top:0;background:#0b1220;z-index:5;padding:4px 0 8px}
.view-nav button{font-size:14px;margin:0;min-height:44px;padding:10px 6px}.view-nav button[aria-pressed=true]{background:#a4f2bf;color:#10231c}
.panel{padding:12px;margin:8px 0;border-radius:15px}h2{font-size:17px;margin:4px 0 10px}.grid{gap:8px}.metric{padding:10px 6px}.value{font-size:clamp(21px,6.4vw,29px);margin-top:2px;overflow-wrap:anywhere}.hero .metric small{font-size:12px}.calorie-row{display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding:8px 12px}.calorie-row .value{font-size:23px}.calorie-row small{max-width:60%;text-align:left}
button{min-height:46px;padding:12px 8px;margin:4px 0}#status{font-size:12px;margin-top:8px}#toast{font-size:12px;min-height:0}#toast:empty{display:none}.compact-notice{font-size:11px;margin:6px 0}.compact-details{margin:8px 0}.compact-details>summary{color:#edf3ff;min-height:28px;line-height:28px;font-weight:700}.compact-details[open]>summary{margin-bottom:10px}
.record{border:1px solid #293951;border-radius:14px;padding:12px;margin-top:10px;background:#0d182a}.record-date{font-size:13px;color:#a6b5cf}.record-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}.record-stat small{font-size:11px}.record-stat strong{display:block;font-size:20px;font-variant-numeric:tabular-nums}.record-stat span{font-size:12px;font-weight:400;color:#a6b5cf}.record details{margin:8px 0}.record button{min-height:44px}.record summary{min-height:40px;line-height:40px}.record .sub{font-size:12px;overflow-wrap:anywhere}.record-kcal{font-size:13px;color:#a4f2bf}
@media(max-width:360px){main{padding-left:8px;padding-right:8px}.metric{padding:8px 4px}.value{font-size:21px}}
</style><link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet"/><style>.view-nav{grid-template-columns:repeat(4,1fr)}#map-canvas{height:clamp(260px,52dvh,430px);border-radius:14px;z-index:0}.phone-arrow{font-size:32px;color:#0073ff;text-shadow:0 0 3px white;line-height:36px;text-align:center}.map-note{font-size:12px;line-height:1.5;margin:6px 0}.leaflet-control-attribution{font-size:10px}</style></head><body><main><div class="app-header"><strong>🏃 QR RUN</strong><span>나만의 러닝</span></div><section class="panel" id="login-screen"><h1 style="font-size:25px">구글 계정으로 러닝 기록 보관</h1><p class="sub">같은 구글 계정으로 로그인하면 다른 기기에서도 저장한 기록을 불러옵니다.</p><button class="primary" disabled="" id="google-login">Google로 로그인</button><p class="sub" id="auth-status" role="status">로그인 서비스를 연결하는 중입니다…</p><small>Chrome 또는 Safari에서 열어 주세요. 팝업을 허용해야 합니다. 계정별 기록은 Firebase에 저장되며 저장 시 GPS 이동 경로도 본인 계정에 보관합니다.</small></section><section class="panel" hidden="" id="onboarding"><div class="tag">READY TO RUN</div><h1 style="font-size:26px;margin:12px 0">먼저 체중을 알려주세요</h1><p class="sub">체중과 달린 거리로 예상 소모 칼로리를 계산합니다.</p><form id="weight-form" novalidate=""><label for="initial-weight">내 체중 (kg)</label><input aria-describedby="weight-error weight-range" id="initial-weight" inputmode="decimal" max="300" min="20" placeholder="예: 65.5" required="" step="0.1" style="width:100%;padding:18px 14px;font-size:28px;border-radius:12px;border:1px solid #52647e;background:#0d182a;color:#edf3ff;box-sizing:border-box" type="number"/><small id="weight-range">20~300kg · 소수점 첫째 자리까지 입력</small><p id="weight-error" role="alert" style="color:#ffc8d1;min-height:20px"></p><button class="primary" type="submit">시작하기 →</button></form><p class="sub" style="font-size:12px">시작하기는 기본 화면으로 이동하는 버튼입니다. GPS 측정은 다음 화면에서 시작해 주세요.</p><small>칼로리는 평지 달리기용 추정값이며 실제 소모량과 다를 수 있습니다. 체중은 설정에서 바꿀 수 있습니다.</small></section><div hidden="" id="app-shell"><nav aria-label="앱 화면" class="view-nav"><button aria-pressed="true" id="nav-run" type="button">러닝</button><button aria-pressed="false" id="nav-history" type="button">내 기록</button><button aria-pressed="false" id="nav-map" type="button">지도</button><button aria-pressed="false" id="nav-settings" type="button">설정</button></nav><div id="view-run"><section class="panel hero"><div class="grid"><div class="metric"><small>총 뛴 거리</small><div class="value"><span id="distance">0.00</span> <small>km</small></div></div><div class="metric"><small>총 운동 시간</small><div class="value" id="time">00:00:00</div></div><div class="metric"><small>평균 시속</small><div class="value"><span id="speed">0.0</span> <small>km/h</small></div></div><div class="metric"><small>평균 페이스</small><div class="value" id="pace">—</div><small>1km당 분:초</small></div></div><div class="metric calorie-row"><small>예상 활동 칼로리 · 안정 시 소모량 제외</small><div class="value"><span id="calories">0</span> kcal</div></div></section><div class="grid"><button class="primary" id="start">▶ 시작</button><button class="danger" disabled="" id="stop">■ 종료</button></div><button disabled="" id="save">💾 이번 러닝 저장</button><div id="status" role="status">시작을 누르면 위치 권한을 요청합니다.</div><div aria-live="polite" id="toast"></div><p class="notice compact-notice">화면을 켜두고 달려 주세요. GPS·칼로리는 추정값입니다.</p><details class="panel compact-details"><summary>속도 변화 · 최고/최저</summary><div class="grid"><div class="metric"><small>가장 빠른 시속</small><div class="value" id="fastest">—</div><small id="fastpace">페이스 —</small></div><div class="metric"><small>가장 느린 시속</small><div class="value" id="slowest">—</div><small id="slowpace">페이스 —</small></div></div><p id="variation" style="font-weight:750;line-height:1.8">10초 구간 2개가 쌓이면 속도·페이스 차이를 표시합니다.</p><small>최고·최저는 유효한 10초 구간 평균입니다. 정지 구간도 포함합니다. 차이가 클수록 속도 변화가 큽니다. GPS 수신 공백은 제외하며, GPS 오차가 반영될 수 있습니다.</small><div class="sub">GPS 정확도 <b id="accuracy">—</b></div></details><details class="panel compact-details"><summary>1km 구간 기록</summary><div id="splits"></div></details></div><div hidden="" id="view-history"><section class="panel"><h2>내 러닝 기록</h2><p class="sub" id="history-summary"></p><small>구글 계정에 저장된 기록입니다. 같은 계정이면 다른 기기에서도 조회할 수 있습니다.</small><div><button id="refresh-records">↻ 클라우드 기록 새로고침</button><button hidden="" id="import-local">이 브라우저의 예전 기록 가져오기</button><button hidden="" id="recover-draft">저장 대기 기록 다시 업로드</button><p class="sub" id="cloud-status" role="status"></p></div><div id="records"></div></section></div><div hidden="" id="view-map"><div class="grid"><button id="map-locate">📍 내 위치</button><button id="map-compass">🧭 폰 방향 켜기</button></div><div id="map-canvas"></div><p class="map-note" id="map-status" role="status">내 위치를 누르면 지도를 표시합니다.</p><p class="map-note" id="heading-status">폰 방향 미사용 · 폰을 화면이 위로 향하도록 평평하게 들면 상단 방향을 표시합니다.</p><div class="grid"><button id="map-fit">전체 경로 보기</button><button id="map-current">이번 러닝 경로</button></div><p class="map-note">러닝 시작 후 이동한 곳을 선으로 연결합니다. GPS 공백은 끊어 표시합니다. 지도만 열어서는 운동 기록이 시작되지 않습니다. 센서·GPS 오차가 있어 안전한 길 안내 용도로는 사용하지 마세요.</p></div><div hidden="" id="view-settings"><section class="panel"><h2>구글 계정</h2><p class="sub" id="account-name"></p><button id="logout">로그아웃</button><p class="sub">종료한 러닝은 자동으로 클라우드 저장을 시도합니다. 저장 완료 표시를 확인한 뒤 앱을 닫아 주세요.</p></section><section class="panel"><h2>예상 소모 칼로리</h2><label for="weight">내 체중 (kg)<input id="weight" max="300" min="20" step="0.1" style="width:100px;padding:10px;border-radius:8px;font-size:18px" type="number" value=""/></label><small>처음 입력한 체중입니다. 다음 러닝의 체중은 여기서 변경할 수 있습니다.</small><p class="sub" id="calorieNote"></p><small>평지 달리기 근사식: 체중(kg) × 거리(km) × 1 kcal/kg/km. 속도 × 운동시간으로 계산한 거리와 같은 값입니다. 같은 거리라면 속도가 달라도 이 모델의 추정 칼로리는 같습니다. 걷기·경사·바람·개인 체력은 반영하지 않습니다. 정지 시간은 추가 칼로리로 계산하지 않습니다. 의료용 측정값이 아닙니다.</small></section><section class="panel"><label><input checked="" id="voice" type="checkbox"/>1km마다 천천히 음성 안내</label><button id="test">🔊 음성 테스트</button></section><div class="notice">정확한 측정을 위해 야외에서 사용하고, 휴대폰 화면을 켜두세요. 화면 잠금·백그라운드에서는 GPS와 음성이 중단될 수 있습니다. GPS 오차로 실제 거리와 차이가 날 수 있습니다.</div><details><summary>사용 방법과 위치 권한 안내</summary><div class="sub"><p>① 시작 → 위치 허용 → GPS 수신 확인 → 달리기<br/>② 종료 → 이번 러닝 저장<br/>③ 저장 기록에서 개별 삭제</p><p>앱은 HTTPS 주소로 열어야 합니다. 카카오톡·네이버 등의 앱 내부 브라우저 대신 Safari 또는 Chrome으로 직접 여세요. 위치 권한은 브라우저와 휴대폰 설정에서 모두 허용해야 합니다.</p><p>위치가 차단되면 배포 사이트의 iframe 위치 권한 정책 때문일 수 있습니다. 브라우저가 위치 사용을 막는 배포 환경에서는 이 웹앱으로 우회할 수 없습니다.</p><p>시간 측정은 첫 유효 GPS 수신부터 시작합니다. 페이스는 경과 시간 ÷ GPS 이동 거리이며, 정지 시간도 포함합니다. 정확도 35m 초과, 3m 미만 이동, 시속 43.2km 초과 점프는 걸러냅니다. 실제 이동 일부도 제외될 수 있어 전문 운동기기와 일치하지 않을 수 있습니다.</p><p>주행 중에는 새로고침하거나 페이지를 닫지 마세요. 저장 전 러닝은 보존되지 않습니다. 저장한 거리·시간·구간 기록·체중·예상 칼로리는 구글 계정별 Firebase 데이터베이스에 보관됩니다. 저장 시 GPS 경로도 본인 계정에 업로드합니다.</p></div></details></div></div></main><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
'use strict';
const $=id=>document.getElementById(id);
const KEY='qr_run_records_v1';
const FIREBASE_CONFIG=__FIREBASE_CONFIG__;
let fb=null,auth=null,db=null,cloudUser=null,saving=false,loadingRecords=false,runId=null,legacyRecords=[],cloudBusy=false;
let authSession=0;
function cloudMessage(text){$('cloud-status').textContent=text;}
function errorText(e){
 const code=e?.code||'';
 const known={'auth/popup-blocked':'팝업이 차단되었습니다. 팝업을 허용한 뒤 다시 눌러 주세요.', 'auth/popup-closed-by-user':'로그인 창이 닫혔습니다. 다시 로그인해 주세요.', 'auth/unauthorized-domain':'Firebase Authentication의 승인된 도메인에 현재 앱 도메인을 추가해야 합니다.', 'auth/operation-not-allowed':'Firebase에서 Google 로그인 제공업체를 켜 주세요.', 'permission-denied':'저장 권한이 없습니다. Firestore 보안 규칙과 로그인 상태를 확인하세요.', 'unavailable':'서버 연결이 불안정합니다. 인터넷 연결을 확인하고 다시 시도하세요.', 'deadline-exceeded':'서버 응답 확인이 지연되고 있습니다. 기록을 새로고침한 후 다시 확인해 주세요.'};
 return known[code]||('처리하지 못했습니다. '+(code||'네트워크·Firebase 설정을 확인해 주세요.'));
}
function withTimeout(promise){let timer;return Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject({code:'deadline-exceeded'}),20000);})]).finally(()=>clearTimeout(timer));}
function validRecord(r){return r&&typeof r.id==='string'&&/^[A-Za-z0-9_-]{1,128}$/.test(r.id)&&Number.isFinite(r.distance)&&r.distance>=0&&Number.isFinite(r.seconds)&&r.seconds>=0&&Number.isFinite(r.date);}
function draftKey(){return cloudUser?'qr_run_pending_'+cloudUser.uid:null;}
function refreshRecovery(){let exists=false;try{const k=draftKey();exists=!!(k&&localStorage.getItem(k));}catch(e){}$('recover-draft').hidden=!exists;}
function backupDraft(r){try{localStorage.setItem(draftKey(),JSON.stringify(r));refreshRecovery();}catch(e){/* Cloud saving still works if browser storage is unavailable. */}}
function clearDraft(id){try{const key=draftKey(),r=JSON.parse(localStorage.getItem(key)||'null');if(r?.id===id)localStorage.removeItem(key);}catch(e){}refreshRecovery();}

let records=[],storageOK=true,watchId=null,running=false,pending=false,startAt=0,endAt=0,total=0,last=null,splits=[],lastSplitTime=0,saved=false,wakeLock=null, speedStats={count:0,min:null,max:null}, speedAnchor=null, runWeight=null, editingWeight=false, profileReady=false;
try{const raw=JSON.parse(localStorage.getItem(KEY)||'[]');if(Array.isArray(raw))legacyRecords=raw.filter(validRecord);}catch(e){}

let runMap=null,mapLine=null,positionMarker=null,accuracyCircle=null,mapPosition=null;
let routeSegments=[],displayingHistory=false,phoneHeading=null,orientationEnabled=false,locating=false;
function ensureMap(){
 if(runMap)return true;
 if(!window.L){$('map-status').textContent='지도 라이브러리를 불러오지 못했습니다. 인터넷을 확인하고 새로고침하세요.';return false;}
 runMap=L.map('map-canvas').setView([36.5,127.8],7);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'}).addTo(runMap);
 mapLine=L.polyline([],{color:'#ff4b6e',weight:5,opacity:.9}).addTo(runMap);
 drawRoute(routeSegments);return true;
}
function drawRoute(segments){if(mapLine)mapLine.setLatLngs(segments.map(seg=>seg.map(p=>[p.lat,p.lng])));}
function fitRoute(){if(!ensureMap())return;const bounds=mapLine.getBounds();if(bounds.isValid())runMap.fitBounds(bounds,{padding:[24,24],maxZoom:18});else if(mapPosition)runMap.setView(mapPosition,17);}
function showHeading(h,source){
 if(!Number.isFinite(h))return;const angle=((h%360)+360)%360;
 if(positionMarker)positionMarker.setIcon(L.divIcon({className:'',html:'<div class="phone-arrow" style="transform:rotate('+angle+'deg)">▲</div>',iconSize:[36,36],iconAnchor:[18,18]}));
 $('heading-status').textContent=source+' · 北 기준 '+Math.round(angle)+'°'+(source==='폰 방향'?' · 센서 오차에 주의하세요.':' · 폰이 바라보는 방향과 다릅니다.');
}
function updateMapPosition(pos,center=false){
 const c=pos.coords;if(!Number.isFinite(c.latitude)||!Number.isFinite(c.longitude))return;
 mapPosition=[c.latitude,c.longitude];
 if(!runMap&&!center)return;if(!ensureMap())return;
 if(!positionMarker){positionMarker=L.marker(mapPosition).addTo(runMap);accuracyCircle=L.circle(mapPosition,{radius:Math.min(c.accuracy||0,10000),weight:1,fillOpacity:.1}).addTo(runMap);}
 else{positionMarker.setLatLng(mapPosition);accuracyCircle.setLatLng(mapPosition).setRadius(Math.min(c.accuracy||0,10000));}
 if(phoneHeading!==null)showHeading(phoneHeading,'폰 방향');else if(Number.isFinite(c.heading)&&c.speed>0.5)showHeading(c.heading,'GPS 이동 방향');
 if(center)runMap.setView(mapPosition,17);
 $('map-status').textContent='현재 위치 · GPS 오차 약 ±'+Math.round(c.accuracy||0)+'m'+(displayingHistory?' · 저장된 경로를 보는 중':' · 이번 러닝 경로');
}
function routePoint(p,newSegment=false){
 if(!routeSegments.length||newSegment)routeSegments.push([]);
 const seg=routeSegments[routeSegments.length-1];seg.push({lat:p.latitude,lng:p.longitude});
 // Bound Firestore document size while retaining endpoints and path breaks.
 if(routeSegments.reduce((n,a)=>n+a.length,0)>3000)routeSegments=routeSegments.map(a=>a.filter((_,i)=>i===0||i===a.length-1||i%2===0));
 if(!displayingHistory)drawRoute(routeSegments);
}
function resetRoute(){routeSegments=[];displayingHistory=false;drawRoute([]);}
$('map-locate').onclick=()=>{
 if(locating)return;if(!navigator.geolocation){$('map-status').textContent='이 브라우저는 위치 기능을 지원하지 않습니다.';return;}
 locating=true;$('map-status').textContent='위치 권한과 GPS를 확인하는 중…';
 navigator.geolocation.getCurrentPosition(pos=>{locating=false;updateMapPosition(pos,true);},e=>{locating=false;$('map-status').textContent='위치 확인 실패. 위치 권한·HTTPS·야외 수신 상태를 확인하세요. ('+e.code+')';},{enableHighAccuracy:true,timeout:20000,maximumAge:3000});
};
function orientation(e){
 let h=null;
 if(Number.isFinite(e.webkitCompassHeading)&&(!Number.isFinite(e.webkitCompassAccuracy)||e.webkitCompassAccuracy>=0))h=e.webkitCompassHeading;
 else if(e.absolute===true&&Number.isFinite(e.alpha))h=360-e.alpha;
 if(h!==null){phoneHeading=((h%360)+360)%360;showHeading(phoneHeading,'폰 방향');}
}
$('map-compass').onclick=async()=>{
 try{
 if(typeof DeviceOrientationEvent==='undefined')throw Error('미지원');
 if(typeof DeviceOrientationEvent.requestPermission==='function'&&await DeviceOrientationEvent.requestPermission()!=='granted')throw Error('권한 거부');
 if(!orientationEnabled){window.addEventListener('deviceorientationabsolute',orientation);window.addEventListener('deviceorientation',orientation);orientationEnabled=true;}
 $('heading-status').textContent='나침반 신호 대기 중… 폰을 평평하게 들고 센서 권한을 허용하세요. 신호가 없으면 이 브라우저에서 폰 방향을 지원하지 않을 수 있습니다.';
 }catch(e){$('heading-status').textContent='폰 방향을 사용할 수 없습니다. 센서 권한과 Safari/Chrome 설정을 확인하세요. 이동 중에는 GPS 이동 방향만 표시할 수 있습니다.';}
};
$('map-fit').onclick=fitRoute;
$('map-current').onclick=()=>{displayingHistory=false;drawRoute(routeSegments);fitRoute();$('map-status').textContent='이번 러닝 경로를 표시합니다.';};
function showSavedRoute(r){switchView('map');if(!ensureMap())return;displayingHistory=true;drawRoute(r.route);fitRoute();$('map-status').textContent='저장된 러닝 경로 · '+new Date(r.date).toLocaleString('ko-KR');}
function duration(s){s=Math.max(0,Math.floor(s));return [Math.floor(s/3600),Math.floor(s/60)%60,s%60].map(v=>String(v).padStart(2,'0')).join(':');}
function pace(s){if(!Number.isFinite(s)||s<=0)return '—';let n=Math.round(s);return Math.floor(n/60)+':'+String(n%60).padStart(2,'0');}
function validWeight(){const w=Number($('weight').value);return Number.isFinite(w)&&w>=20&&w<=300?w:null;}
function estimateCalories(weight,meters){return weight===null?null:weight*Math.max(0,meters)/1000;}
function updateCalories(){
 const w=startAt||running||pending?runWeight:validWeight();
 const kcal=estimateCalories(w,total);
 $('calories').textContent=kcal===null?'—':Math.round(kcal).toLocaleString('ko-KR');
 $('calorieNote').textContent=w===null?'체중을 20~300kg 범위로 입력해 주세요.':`체중 ${w}kg 기준 · GPS 거리로 추정 · 달리기용 근사값`;
 $('weight').disabled=running||pending||(Boolean(startAt)&&!editingWeight);
}
$('weight').addEventListener('input',updateCalories);
$('weight-form').addEventListener('submit',event=>{
 event.preventDefault();if(!cloudUser)return;const input=$('initial-weight');const value=Number(input.value);
 if(input.value.trim()===''||!Number.isFinite(value)||value<20||value>300||Math.abs(value*10-Math.round(value*10))>1e-7){
  $('weight-error').textContent='체중을 20~300kg 범위에서 소수점 첫째 자리까지 입력해 주세요.';
  input.setAttribute('aria-invalid','true');input.focus();return;
 }
 input.removeAttribute('aria-invalid');$('weight-error').textContent='';$('weight').value=String(value);profileReady=true;
 $('onboarding').hidden=true;$('app-shell').hidden=false;updateCalories();switchView('run');
 $('start').focus({preventScroll:true});
});
$('initial-weight').addEventListener('input',()=>{$('weight-error').textContent='';$('initial-weight').removeAttribute('aria-invalid');});

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
function update(){updateCalories();updateVariation();const sec=elapsed(),km=total/1000;$('distance').textContent=km.toFixed(2);$('time').textContent=duration(sec);$('pace').textContent=km>0?pace(sec/km):'—';$('speed').textContent=sec>0?(km/(sec/3600)).toFixed(1):'0.0';$('start').disabled=running||pending||saving||cloudBusy||!cloudUser;$('logout').disabled=running||pending||saving||cloudBusy||loadingRecords;$('stop').disabled=!running&&!pending;$('save').disabled=running||pending||!startAt||!total||saved||saving||cloudBusy||!cloudUser;}
function speak(text){if(!('speechSynthesis' in window)){$('toast').textContent='이 브라우저는 음성 안내를 지원하지 않습니다.';return;}const u=new SpeechSynthesisUtterance(text);u.lang='ko-KR';u.rate=0.78;u.pitch=1;const voices=speechSynthesis.getVoices();const ko=voices.find(v=>v.lang.toLowerCase().startsWith('ko'));if(ko)u.voice=ko;u.onerror=()=>{$('toast').textContent='음성 재생이 제한되었습니다. 화면의 구간 기록을 확인하세요.';};speechSynthesis.speak(u);}
$('test').onclick=()=>speak('음성 안내입니다. 1킬로미터 완료. 이번 구간 페이스, 6분 30초. 시속, 9점 2킬로미터입니다.');
function haversine(a,b){const r=Math.PI/180,dLat=(b.latitude-a.latitude)*r,dLon=(b.longitude-a.longitude)*r;const h=Math.sin(dLat/2)**2+Math.cos(a.latitude*r)*Math.cos(b.latitude*r)*Math.sin(dLon/2)**2;return 6371000*2*Math.asin(Math.sqrt(Math.min(1,h)));}
async function lock(){try{if('wakeLock' in navigator)wakeLock=await navigator.wakeLock.request('screen');}catch(e){/* Optional; unsupported browsers still run. */}}
function unlock(){if(wakeLock){wakeLock.release().catch(()=>{});wakeLock=null;}}
function renderSplits(){const node=$('splits');node.replaceChildren();if(!splits.length){node.textContent='1km를 달리면 구간별 페이스와 속도가 표시됩니다.';node.className='empty';return;}node.className='';const table=document.createElement('table');const header=document.createElement('tr');for(const text of ['구간','구간 페이스','구간 속도']){const th=document.createElement('th');th.textContent=text;header.append(th);}table.append(header);for(const s of splits){const tr=document.createElement('tr');for(const text of [s.km+' km',pace(s.seconds)+' /km',s.speed.toFixed(1)+' km/h']){const td=document.createElement('td');td.textContent=text;tr.append(td);}table.append(tr);}node.append(table);}
function position(pos){if(!running&&!pending)return;updateMapPosition(pos);const c=pos.coords;$('accuracy').textContent=Number.isFinite(c.accuracy)?'±'+Math.round(c.accuracy)+'m':'—';if(!Number.isFinite(c.latitude)||!Number.isFinite(c.longitude)||!Number.isFinite(c.accuracy)||c.accuracy>35){speedAnchor=null;$('status').textContent='GPS 정확도가 낮습니다. 하늘이 잘 보이는 곳에서 기다려 주세요. 해당 위치는 거리에 반영하지 않습니다.';return;}
const now=Date.now();const p={latitude:c.latitude,longitude:c.longitude,timestamp:pos.timestamp};
if(pending){routePoint(p,true);sampleSpeed(p.timestamp,0);pending=false;running=true;startAt=now;lastSplitTime=0;last=p;$('status').textContent='🟢 GPS 연결 완료. 거리와 시간 측정을 시작했습니다.';if($('voice').checked)speak('측정을 시작합니다. 안전하게 달리세요.');lock();update();return;}
const gap=(p.timestamp-last.timestamp)/1000;if(gap<=0)return;
if(gap>20){routePoint(p,true);speedAnchor=null;sampleSpeed(p.timestamp,total);last=p;$('status').textContent='GPS 수신 공백이 감지되었습니다. 누락된 구간은 추정하지 않고 현재 위치에서 측정을 이어갑니다.';return;}
const d=haversine(last,p);if(d/gap>12){routePoint(p,true);speedAnchor=null;last=p;$('status').textContent='비정상적인 GPS 위치 이동을 제외했습니다.';return;}
if(d<3){sampleSpeed(p.timestamp,total);update();return;}
const old=total;const previousSec=Math.max(0,(last.timestamp-startAt)/1000);const currentSec=Math.max(previousSec,(p.timestamp-startAt)/1000);total+=d;routePoint(p);sampleSpeed(p.timestamp,total);
while(total>=(splits.length+1)*1000){const km=splits.length+1;const ratio=(km*1000-old)/d;const crossing=previousSec+(currentSec-previousSec)*ratio;const seconds=Math.max(.001,crossing-lastSplitTime);lastSplitTime=crossing;const speed=3600/seconds;splits.push({km,seconds,speed});if($('voice').checked){const n=Math.round(seconds),speedText=speed.toFixed(1).replace('.','점 ');speak(`${km}킬로미터 완료. 이번 1킬로미터 구간 페이스, ${Math.floor(n/60)}분 ${n%60}초. 시속, ${speedText}킬로미터입니다.`);}renderSplits();}
last=p;$('status').textContent='🟢 측정 중 · 1km마다 구간 페이스와 속도를 알려드립니다.';update();}
function geoError(error){if(!pending&&!running)return;const reason={1:'위치 권한이 거부되었거나 배포 환경의 위치 권한 정책으로 차단되었습니다. Chrome/Safari에서 주소를 직접 열고 위치 권한을 확인하세요.',2:'현재 위치를 찾을 수 없습니다. 휴대폰 위치 설정과 야외 수신 상태를 확인하세요.',3:'GPS 수신 시간이 초과되었습니다. 야외에서 잠시 기다려 주세요.'};$('status').textContent=reason[error.code]||'GPS 오류가 발생했습니다.';if(error.code===1){stop(false);} }
$('start').onclick=()=>{if(!profileReady||!cloudUser||saving||cloudBusy)return;const chosenWeight=validWeight();if(chosenWeight===null){$('status').textContent='체중을 20~300kg 범위로 입력해 주세요.';return;}if(!navigator.geolocation){$('status').textContent='이 브라우저는 GPS 위치 측정을 지원하지 않습니다.';return;}if(!window.isSecureContext){$('status').textContent='GPS 사용에는 HTTPS 주소가 필요합니다.';return;}if(startAt&&!saved&&!confirm('저장하지 않은 이번 기록을 버리고 새 러닝을 시작할까요?'))return;
if('speechSynthesis' in window)speechSynthesis.cancel();runId=(crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+'-'+Math.random().toString(36).slice(2));resetRoute();editingWeight=false;runWeight=chosenWeight;startAt=0;endAt=0;total=0;last=null;splits=[];lastSplitTime=0;saved=false;speedStats={count:0,min:null,max:null};speedAnchor=null;pending=true;renderSplits();$('toast').textContent='';$('status').textContent='위치 권한을 허용해 주세요. 정확한 GPS 위치를 기다리는 중입니다…';update();if($('voice').checked)speak('위치를 확인하고 있습니다.');try{watchId=navigator.geolocation.watchPosition(position,geoError,{enableHighAccuracy:true,maximumAge:0,timeout:20000});}catch(e){pending=false;$('status').textContent='위치 측정을 시작하지 못했습니다. 브라우저 권한과 배포 환경을 확인하세요.';update();}};
function stop(announce=true){if(watchId!==null){navigator.geolocation.clearWatch(watchId);watchId=null;}endAt=Date.now();running=false;pending=false;unlock();if(announce){$('status').textContent=startAt?'측정을 종료했습니다. 클라우드 저장 완료 표시를 확인하세요.':'GPS 수신 대기를 취소했습니다.';if(startAt&&$('voice').checked)speak('측정을 종료했습니다. 기록을 저장해 주세요.');}update();}
$('stop').onclick=()=>{stop();if(startAt&&total>0)saveRun();};
const weightHelp=document.createElement('small');weightHelp.textContent='러닝 중·종료 후에는 계산 기준 체중이 고정됩니다. 다음 러닝의 체중을 바꾸려면 아래 버튼을 누르세요.';const weightEdit=document.createElement('button');weightEdit.textContent='다음 러닝 체중 변경';weightEdit.onclick=()=>{if(running||pending){$('toast').textContent='종료 후 변경해 주세요.';return;}editingWeight=true;$('weight').disabled=false;$('weight').focus();};$('weight').parentElement.after(weightHelp,weightEdit);
async function loadRecords(){
 if(!cloudUser||loadingRecords)return;loadingRecords=true;update();const uid=cloudUser.uid,session=authSession;
 cloudMessage('클라우드 기록을 불러오는 중…');
 try{const snapshot=await withTimeout(fb.getDocsFromServer(fb.collection(db,'users',uid,'runs')));
 if(session!==authSession)return;
 records=snapshot.docs.map(d=>({...d.data(),id:d.id})).filter(validRecord);renderRecords();cloudMessage(`클라우드 기록 ${records.length}개를 불러왔습니다.`);
 }catch(e){if(session===authSession)cloudMessage('기록을 불러오지 못했습니다. '+errorText(e));}
 finally{if(session===authSession){loadingRecords=false;update();}}
}
async function uploadRecord(r){
 if(!cloudUser)throw {code:'unauthenticated'};if(!validRecord(r))throw {code:'invalid-argument'};
 const session=authSession,uid=cloudUser.uid;
 await withTimeout(fb.setDoc(fb.doc(db,'users',uid,'runs',r.id),r));
 if(session!==authSession)throw {code:'unauthenticated'};
 records=[r,...records.filter(x=>x.id!==r.id)];clearDraft(r.id);renderRecords();
}
async function saveRun(){
 if(!cloudUser||!startAt||total<=0||running||pending||saved||saving)return;
 saving=true;update();const r={id:runId,date:startAt,distance:total,seconds:elapsed(),weightKg:runWeight,calories:estimateCalories(runWeight,total),calorieModel:'flat_run_net_1kcal_kg_km_v1',speedStats:{...speedStats},route:routeSegments.map(seg=>seg.map(p=>({...p}))),splits:splits.map(s=>({...s}))};
 backupDraft(r);$('toast').textContent='☁ 클라우드에 저장하는 중입니다. 완료될 때까지 기다려 주세요.';
 try{await uploadRecord(r);saved=true;$('toast').textContent='✓ 구글 계정에 저장 완료. 앱을 닫아도 기록을 다시 불러올 수 있습니다.';cloudMessage('최근 러닝을 클라우드에 저장했습니다.');}
 catch(e){$('toast').textContent='클라우드 저장을 확인하지 못했습니다. '+errorText(e)+' 저장 버튼으로 다시 시도하세요.';}
 finally{saving=false;update();}
}
$('save').onclick=saveRun;
$('refresh-records').onclick=()=>loadRecords();
$('recover-draft').onclick=async()=>{
 if(!cloudUser||cloudBusy||saving)return;let r;
 try{r=JSON.parse(localStorage.getItem(draftKey())||'null');if(!validRecord(r))throw Error();}
 catch(e){cloudMessage('복구할 유효한 저장 대기 기록이 없습니다.');return;}
 cloudBusy=true;update();try{await uploadRecord(r);cloudMessage('저장 대기 기록을 업로드했습니다.');}catch(e){cloudMessage(errorText(e));}finally{cloudBusy=false;update();}
};
$('import-local').onclick=async()=>{
 if(!cloudUser||cloudBusy||saving||!legacyRecords.length)return;
 if(!confirm('이 브라우저에 남은 예전 기록을 현재 로그인한 계정으로 복사할까요? 본인 기록인지 확인해 주세요.'))return;
 cloudBusy=true;update();let count=0;
 try{for(const r of legacyRecords){await uploadRecord(r);count++;}cloudMessage(`예전 기록 ${count}개를 계정으로 복사했습니다. 브라우저의 원본은 유지됩니다.`);$('import-local').hidden=true;}
 catch(e){cloudMessage(`${count}개 복사 완료. 나머지는 다시 가져올 수 있습니다. `+errorText(e));}
 finally{cloudBusy=false;update();}
};
async function deleteRecord(r,button){
 if(!cloudUser||cloudBusy||saving||!confirm('이 기록을 클라우드에서 영구 삭제할까요? 다른 기기에서도 삭제됩니다.'))return;
 cloudBusy=true;button.disabled=true;update();
 try{await withTimeout(fb.deleteDoc(fb.doc(db,'users',cloudUser.uid,'runs',r.id)));records=records.filter(x=>x.id!==r.id);clearDraft(r.id);renderRecords();cloudMessage('클라우드 기록을 삭제했습니다.');}
 catch(e){cloudMessage('삭제를 확인하지 못했습니다. '+errorText(e));button.disabled=false;}
 finally{cloudBusy=false;update();}
}
let visibleRecords=10;
function renderRecords(){
 const node=$('records');node.replaceChildren();
 const sorted=[...records].sort((a,b)=>b.date-a.date);
 $('history-summary').textContent=`총 ${sorted.length}회 · 누적 ${(sorted.reduce((sum,r)=>sum+r.distance,0)/1000).toFixed(2)} km`;
 if(!sorted.length){node.textContent='아직 저장한 기록이 없습니다.';node.className='empty';return;}
 node.className='';
 sorted.slice(0,visibleRecords).forEach(r=>{
  const box=document.createElement('article');box.className='record';
  const date=document.createElement('div');date.className='record-date';date.textContent=new Date(r.date).toLocaleString('ko-KR');box.append(date);
  const grid=document.createElement('div');grid.className='record-grid';const km=r.distance/1000;
  for(const [label,value,unit] of [['거리',km.toFixed(2),'km'],['시간',duration(r.seconds),''],['평균 시속',r.seconds>0?(km*3600/r.seconds).toFixed(1):'0.0','km/h'],['평균 페이스',km>0?pace(r.seconds/km):'—','/km']]){
   const cell=document.createElement('div');cell.className='record-stat';const name=document.createElement('small');name.textContent=label;const number=document.createElement('strong');number.textContent=value+' ';const suffix=document.createElement('span');suffix.textContent=unit;number.append(suffix);cell.append(name,number);grid.append(cell);
  }box.append(grid);
  const energy=document.createElement('div');energy.className='record-kcal';energy.textContent=Number.isFinite(r.calories)&&Number.isFinite(r.weightKg)?`예상 ${Math.round(r.calories).toLocaleString('ko-KR')} kcal · ${r.weightKg}kg 기준`:'칼로리 정보 없음 · 기존 기록';box.append(energy);
  const detail=document.createElement('details');const summary=document.createElement('summary');summary.textContent='속도 변화 · 구간 상세';detail.append(summary);
  const stats=r.speedStats;const variation=document.createElement('p');variation.className='sub';
  variation.textContent=stats&&stats.count>0&&Number.isFinite(stats.min)&&Number.isFinite(stats.max)?`10초 구간 기준 · 최고 ${stats.max.toFixed(1)} km/h (${speedPace(stats.max)}) · 최저 ${stats.min.toFixed(1)} km/h (${speedPace(stats.min)}) · ${variationText(stats)}`:'최고·최저 시속 정보 없음';detail.append(variation);
  if(Array.isArray(r.splits)&&r.splits.length){for(const s of r.splits){const row=document.createElement('p');row.className='sub';row.textContent=`${s.km}km · ${pace(s.seconds)} /km · ${Number(s.speed).toFixed(1)} km/h`;detail.append(row);}}
  else{const empty=document.createElement('p');empty.className='sub';empty.textContent='완료한 1km 구간이 없습니다.';detail.append(empty);}
  if(Array.isArray(r.route)&&r.route.some(seg=>Array.isArray(seg)&&seg.length)){const mapButton=document.createElement('button');mapButton.textContent='🗺 이 기록 경로 보기';mapButton.onclick=()=>showSavedRoute(r);detail.append(mapButton);}
  const del=document.createElement('button');del.className='danger';del.textContent='이 기록 삭제';del.onclick=()=>deleteRecord(r,del);detail.append(del);box.append(detail);node.append(box);
 });
 if(sorted.length>visibleRecords){const more=document.createElement('button');more.textContent='이전 기록 10개 더 보기';more.onclick=()=>{visibleRecords+=10;renderRecords();};node.append(more);}
}
function switchView(name){
 for(const key of ['run','history','map','settings']){$('view-'+key).hidden=key!==name;$('nav-'+key).setAttribute('aria-pressed',String(key===name));}
 if(name==='map'){ensureMap();setTimeout(()=>{if(runMap)runMap.invalidateSize();},80);}if(name==='history')renderRecords();window.scrollTo(0,0);requestAnimationFrame(resize);
}
for(const key of ['run','history','map','settings'])$('nav-'+key).onclick=()=>switchView(key);
window.addEventListener('beforeunload',e=>{if(running||pending||(startAt&&!saved&&total>0)){e.preventDefault();e.returnValue='';}});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&running){lock();$('status').textContent='앱으로 돌아왔습니다. 백그라운드 동안 위치가 누락되었을 수 있습니다.';}});
setInterval(update,250);renderSplits();renderRecords();update();
// Resize this Streamlit component as history grows, without an external JS dependency.
window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:componentReady',apiVersion:1},'*');
function resize(){window.parent.postMessage({isStreamlitMessage:true,type:'streamlit:setFrameHeight',height:Math.ceil(document.querySelector('main').getBoundingClientRect().height)+4},'*');}
new ResizeObserver(resize).observe(document.querySelector('main'));resize();

$('google-login').onclick=async()=>{
 if(!auth)return;$('google-login').disabled=true;$('auth-status').textContent='구글 로그인 창에서 계정을 선택해 주세요.';
 try{const provider=new fb.GoogleAuthProvider();provider.setCustomParameters({prompt:'select_account'});await fb.signInWithPopup(auth,provider);}
 catch(e){$('auth-status').textContent=errorText(e);}
 finally{$('google-login').disabled=false;}
};
$('logout').onclick=async()=>{
 if(!auth||running||pending||saving||cloudBusy||loadingRecords)return;
 if(startAt&&!saved&&total>0&&!confirm('저장하지 않은 기록이 있습니다. 로그아웃할까요?'))return;
 try{await fb.signOut(auth);}catch(e){$('toast').textContent=errorText(e);}
};
async function initCloud(){
 try{
  const version='11.10.0';
  const [appSDK,authSDK,firestoreSDK]=await Promise.all([
   import(`https://www.gstatic.com/firebasejs/${version}/firebase-app.js`),
   import(`https://www.gstatic.com/firebasejs/${version}/firebase-auth.js`),
   import(`https://www.gstatic.com/firebasejs/${version}/firebase-firestore.js`)
  ]);
  fb={...appSDK,...authSDK,...firestoreSDK};const app=fb.initializeApp(FIREBASE_CONFIG);auth=fb.getAuth(app);db=fb.getFirestore(app);
  // Server-confirmed writes, no sensitive offline database cache.
  let persistentLogin=true;try{await fb.setPersistence(auth,fb.browserLocalPersistence);}catch(e){persistentLogin=false;await fb.setPersistence(auth,fb.inMemoryPersistence);}
  fb.onAuthStateChanged(auth,user=>{
   authSession++;loadingRecords=false;
   if(cloudUser?.uid!==user?.uid){if(running||pending)stop(false);resetRoute();mapPosition=null;phoneHeading=null;if(positionMarker){runMap.removeLayer(positionMarker);runMap.removeLayer(accuracyCircle);positionMarker=null;accuracyCircle=null;}records=[];startAt=0;endAt=0;total=0;last=null;splits=[];runWeight=null;runId=null;saved=false;profileReady=false;speedStats={count:0,min:null,max:null};speedAnchor=null;$('initial-weight').value='';$('weight').value='';}
   cloudUser=user;$('login-screen').hidden=!!user;$('onboarding').hidden=!user||profileReady;$('app-shell').hidden=!user||!profileReady;
   if(user){$('account-name').textContent=user.email||user.displayName||'로그인한 사용자';$('import-local').hidden=legacyRecords.length===0;refreshRecovery();loadRecords();}
   else{$('auth-status').textContent='구글 계정으로 로그인해 주세요.'+(persistentLogin?'':' 이 브라우저에서는 재접속 시 다시 로그인해야 합니다. 저장된 계정 기록은 유지됩니다.');$('google-login').disabled=false;}
   renderSplits();renderRecords();update();requestAnimationFrame(resize);
  },e=>{$('auth-status').textContent=errorText(e);$('google-login').disabled=false;});
 }catch(e){$('auth-status').textContent='로그인 서비스 연결에 실패했습니다. 인터넷과 Firebase 설정을 확인하고 새로고침해 주세요. '+(e?.code||'');}
}
initCloud();
</script></body></html>'''
# Serve a real same-origin component URL rather than an about:srcdoc iframe:
# Firebase popup auth checks the current document's URL against authorized domains.
# Assets are created automatically; GitHub still needs only app.py + requirements.txt.
@st.cache_resource
def component_assets():
    return Path(tempfile.mkdtemp(prefix="qr_run_web_"))

assets = component_assets()
web_config = json.dumps({k: firebase_config[k] for k in required}).replace("<", "\\u003c")
(assets / "index.html").write_text(APP.replace("__FIREBASE_CONFIG__", web_config), encoding="utf-8")
runner = components.declare_component("qr_run_cloud", path=str(assets))
runner(key="qr_run_cloud", default=None)
