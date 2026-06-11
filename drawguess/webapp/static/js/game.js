var cur=null,lg=0,color='#000',drawing=false;
var cvs=document.getElementById('cvs'),ctx=cvs.getContext('2d');
ctx.fillStyle='#fff';ctx.fillRect(0,0,400,300);ctx.lineWidth=3;ctx.lineCap='round';

cvs.addEventListener('mousedown',function(e){drawing=true;var r=cvs.getBoundingClientRect();ctx.beginPath();ctx.moveTo(e.clientX-r.left,e.clientY-r.top);});
cvs.addEventListener('mousemove',function(e){if(!drawing)return;var r=cvs.getBoundingClientRect();ctx.strokeStyle=color==='eraser'?'#fff':color;ctx.lineTo(e.clientX-r.left,e.clientY-r.top);ctx.stroke();ctx.beginPath();ctx.moveTo(e.clientX-r.left,e.clientY-r.top);});
cvs.addEventListener('mouseup',function(){drawing=false;ctx.beginPath();});
cvs.addEventListener('mouseleave',function(){drawing=false;});

document.querySelectorAll('.tbtn').forEach(function(b){b.onclick=function(){
document.querySelectorAll('.tbtn').forEach(function(x){x.classList.remove('active');});
if(this.id==='clear'){ctx.fillStyle='#fff';ctx.fillRect(0,0,400,300);return;}
if(this.id==='eraser'){color='eraser';this.classList.add('active');return;}
color=this.dataset.color;this.classList.add('active');};});

function connect(){
var es=new EventSource('./api/stream');
es.onmessage=function(e){
try{var d=JSON.parse(e.data);if(d.error||d.heartbeat)return;cur=d;render(d);}catch(err){}};
es.onerror=function(){es.close();setTimeout(connect,2000);};}

function render(s){
if(!s)return;
var inner=document.getElementById('chatInner'),evs=s.events||[];
for(var i=0;i<evs.length;i++){if(evs[i].gen<=lg)continue;lg=evs[i].gen;
var div=document.createElement('div');div.className='chat-msg '+evs[i].type;div.textContent=evs[i].text||'';inner.appendChild(div);}
var area=document.getElementById('chat');if(area)area.scrollTop=area.scrollHeight;}

function sendGuess(){
// Generate a description of the canvas
var imgData=ctx.getImageData(0,0,400,300).data;
var desc='';
var samples=[];
for(var y=20;y<280;y+=40)for(var x=20;x<380;x+=40){
var i=(y*400+x)*4;var r=imgData[i],g=imgData[i+1],b=imgData[i+2],a=imgData[i+3];
if(a>0&&(r<250||g<250||b<250)){
var cr=r<128?'深':r<200?'中':'浅';var cg=g<128?'深':g<200?'中':'浅';var cb=b<128?'深':b<200?'中':'浅';
var col='';if(r>g&&r>b)col='红';else if(g>r&&g>b)col='绿';else if(b>r&&b>g)col='蓝';else if(r>200&&g>200&&b<100)col='黄';else col='灰';
samples.push('('+Math.floor(x/400*100)+'%,'+Math.floor(y/300*100)+'%)'+col);}}
desc=samples.slice(0,30).join(',');
fetch('./api/decide',{method:'POST',body:new URLSearchParams({value:desc||'空白画布'})});}

document.getElementById('guessBtn').onclick=sendGuess;
document.getElementById('btnExit').onclick=function(){if(!confirm('退出?'))return;fetch('./api/stop',{method:'POST'});window.location.href='./';};
fetch("./api/start",{method:"POST"}).then(function(){connect();});
