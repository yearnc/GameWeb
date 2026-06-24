// ================================================================
// 你画我猜 — Game Logic (Enhanced)
// ================================================================

var cur = null, lg = 0, color = '#000', brushSize = 4, drawing = false;
var cvs = document.getElementById('cvs'), ctx = cvs.getContext('2d');

// Canvas setup
ctx.fillStyle = '#fff';
ctx.fillRect(0, 0, 400, 300);
ctx.lineWidth = brushSize;
ctx.lineCap = 'round';
ctx.lineJoin = 'round';

// Undo stack — stores up to 30 previous states
var undoStack = [];
const MAX_UNDO = 30;

function saveState() {
    undoStack.push(ctx.getImageData(0, 0, 400, 300));
    if (undoStack.length > MAX_UNDO) undoStack.shift();
}

function undo() {
    if (undoStack.length === 0) return;
    var state = undoStack.pop();
    ctx.globalCompositeOperation = 'source-over';
    ctx.putImageData(state, 0, 0);
}

// Flash feedback for undo/clear
function flashBtn(id) {
    var btn = document.getElementById(id);
    if (!btn) return;
    btn.style.transform = 'scale(1.2)';
    btn.style.borderColor = 'var(--accent)';
    setTimeout(function () { btn.style.transform = ''; btn.style.borderColor = ''; }, 150);
}

// ── Drawing (mouse + touch) ───────────────────────────────

function getPos(e) {
    var r = cvs.getBoundingClientRect();
    var sx = 400 / r.width;   // scale from display to logical
    var sy = 300 / r.height;
    return { x: (e.clientX - r.left) * sx, y: (e.clientY - r.top) * sy };
}

function startDraw(e) {
    e.preventDefault();
    drawing = true;
    saveState();
    var p = getPos(e.touches ? e.touches[0] : e);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);

    // Set composite mode
    if (color === 'eraser') {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.lineWidth = brushSize * 2;  // eraser is double width
    } else {
        ctx.globalCompositeOperation = 'source-over';
        ctx.strokeStyle = color;
        ctx.lineWidth = brushSize;
    }
}

function moveDraw(e) {
    if (!drawing) return;
    e.preventDefault();
    var p = getPos(e.touches ? e.touches[0] : e);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
}

function endDraw() {
    drawing = false;
    ctx.globalCompositeOperation = 'source-over';
    ctx.lineWidth = brushSize;
    ctx.beginPath();
}

// Mouse events
cvs.addEventListener('mousedown', startDraw);
cvs.addEventListener('mousemove', moveDraw);
cvs.addEventListener('mouseup', endDraw);
cvs.addEventListener('mouseleave', endDraw);

// Touch events
cvs.addEventListener('touchstart', startDraw, { passive: false });
cvs.addEventListener('touchmove', moveDraw, { passive: false });
cvs.addEventListener('touchend', endDraw);
cvs.addEventListener('touchcancel', endDraw);

// ── Toolbar ───────────────────────────────────────────────

document.querySelectorAll('.tbtn').forEach(function (b) {
    b.onclick = function () {
        // Clear button
        if (this.id === 'clear') {
            saveState();
            ctx.globalCompositeOperation = 'source-over';
            ctx.fillStyle = '#fff';
            ctx.fillRect(0, 0, 400, 300);
            flashBtn('clear');
            return;
        }
        // Undo button
        if (this.id === 'undo') {
            undo();
            flashBtn('undo');
            return;
        }
        // Eraser
        if (this.id === 'eraser') {
            color = 'eraser';
            document.querySelectorAll('.tbtn').forEach(function (x) { x.classList.remove('active'); });
            this.classList.add('active');
            return;
        }
        // Color buttons
        document.querySelectorAll('.tbtn').forEach(function (x) { x.classList.remove('active'); });
        color = this.dataset.color;
        this.classList.add('active');
    };
});

// ── Brush Size ──────────────────────────────────────────

document.querySelectorAll('#sizes .sbtn').forEach(function (b) {
    b.onclick = function () {
        document.querySelectorAll('#sizes .sbtn').forEach(function (x) { x.classList.remove('active'); });
        this.classList.add('active');
        brushSize = parseInt(this.dataset.size);
        ctx.lineWidth = brushSize;
    };
});

// ── SSE Connection ────────────────────────────────────────

function connect() {
    var es = new EventSource('./api/stream');
    es.onmessage = function (e) {
        try {
            var d = JSON.parse(e.data);
            if (d.error || d.heartbeat) return;
            cur = d;
            render(d);
        } catch (err) { }
    };
    es.onerror = function () { es.close(); setTimeout(connect, 2000); };
}

function render(s) {
    if (!s) return;
    var inner = document.getElementById('chatInner'),
        evs = s.events || [];
    for (var i = 0; i < evs.length; i++) {
        if (evs[i].gen <= lg) continue;
        lg = evs[i].gen;
        var div = document.createElement('div');
        div.className = 'chat-msg ' + evs[i].type;
        div.textContent = evs[i].text || '';
        inner.appendChild(div);
    }
    var area = document.getElementById('chat');
    if (area) area.scrollTop = area.scrollHeight;
}

// ── Canvas Sampling + Image Submit ───────────────────────

function sendGuess() {
    // 1. Export canvas as base64 PNG image
    var imgBase64 = cvs.toDataURL('image/png').split(',')[1];  // strip "data:image/png;base64,"

    // 2. Also generate text description as fallback
    var imgData = ctx.getImageData(0, 0, 400, 300).data;
    var samples = [];
    for (var y = 8; y < 292; y += 15) {
        for (var x = 8; x < 392; x += 15) {
            var i = (y * 400 + x) * 4;
            var r = imgData[i], g = imgData[i + 1], b = imgData[i + 2], a = imgData[i + 3];
            if (a < 10 || (r > 250 && g > 250 && b > 250)) continue;
            var brightness = (r + g + b) / 3;
            var brightLabel = brightness < 80 ? '深' : brightness < 170 ? '' : '浅';
            var colName = '';
            if (Math.max(r, g, b) - Math.min(r, g, b) < 20) {
                colName = brightLabel + (brightness < 80 ? '黑' : brightness > 200 ? '白' : '灰');
            } else if (r > g + 40 && r > b + 40) colName = brightLabel + '红';
            else if (g > r + 40 && g > b + 40) colName = brightLabel + '绿';
            else if (b > r + 40 && b > g + 40) colName = brightLabel + '蓝';
            else if (r > 180 && g > 180 && b < 100) colName = brightLabel + '黄';
            else if (r > 180 && g < 120 && b > 180) colName = brightLabel + '紫';
            else if (r > 200 && g > 140 && b < 100) colName = brightLabel + '橙';
            else if (r < 100 && g > 140 && b > 140) colName = brightLabel + '青';
            else colName = '彩色';
            var pctX = Math.floor((x / 400) * 100), pctY = Math.floor((y / 300) * 100);
            samples.push('(' + pctX + '%,' + pctY + '%)' + colName);
        }
    }
    var textDesc = samples.length > 0 ? samples.slice(0, 80).join(',') : '空白画布';

    // Send both image and text description
    var body = new URLSearchParams();
    body.append('image', imgBase64);
    body.append('value', textDesc);
    fetch('./api/decide', { method: 'POST', body: body });
}

// ── Init ──────────────────────────────────────────────────

document.getElementById('guessBtn').onclick = function () {
    sendGuess();
    // Brief loading indication
    var btn = this;
    btn.textContent = 'AI 正在猜…';
    btn.disabled = true;
    setTimeout(function () { btn.textContent = '让 AI 猜！'; btn.disabled = false; }, 2000);
};

document.getElementById('btnExit').onclick = function () {
    if (!confirm('确定要退出吗？画作不会被保存哦~')) return;
    fetch('./api/stop', { method: 'POST' });
    window.location.href = './';
};

// Initial save for undo
saveState();
fetch('./api/start', { method: 'POST' }).then(function () { connect(); });
