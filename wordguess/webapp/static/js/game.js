var cur=null,lg=0;
fetch('./api/start',{method:'POST'}).then(function(){connect();});
function connect(){
var es=new EventSource('./api/stream');
es.onmessage=function(e){
try{var d=JSON.parse(e.data);if(d.error||d.heartbeat)return;cur=d;render(d);}catch(err){}};
es.onerror=function(){es.close();setTimeout(connect,2000);};}
function render(s){
if(!s)return;document.getElementById('s').textContent='得分: '+s.score;
var inner=document.getElementById('chatInner'),evs=s.events||[];
for(var i=0;i<evs.length;i++){if(evs[i].gen<=lg)continue;lg=evs[i].gen;
if(evs[i].type==='player')continue; // 已经在本地显示了
var div=document.createElement('div');div.className='chat-msg '+evs[i].type;div.textContent=evs[i].text||'';inner.appendChild(div);}
var area=document.getElementById('chat');if(area)area.scrollTop=area.scrollHeight;
var w=s.waiting===true;document.getElementById('inputBar').style.display=w&&!s.over?'flex':'none';
if(w){document.getElementById('inp').disabled=false;document.getElementById('inp').focus();}}
function send(){var v=document.getElementById('inp').value.trim();if(!v)return;document.getElementById('inp').value='';
document.getElementById('inp').disabled=true;
// 立刻显示玩家消息
var inner=document.getElementById('chatInner');
var div=document.createElement('div');div.className='chat-msg player';div.textContent='❓ '+v;inner.appendChild(div);
var area=document.getElementById('chat');if(area)area.scrollTop=area.scrollHeight;
fetch('./api/decide',{method:'POST',body:new URLSearchParams({value:v})});}
document.getElementById('send').onclick=send;
document.getElementById('inp').addEventListener('keydown',function(e){if(e.key==='Enter')send();});
document.getElementById('btnExit').onclick=function(){if(!confirm('退出?'))return;fetch('./api/stop',{method:'POST'});window.location.href='./';};
