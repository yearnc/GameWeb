// === 海龟汤 — SSE Client ===

var currentState = null;
var lastEventGen = 0;
var isWaiting = false;

// ── SSE ─────────────────────────────────────────────────

function connectSSE() {
    var es = new EventSource('./api/stream');
    es.onmessage = function(e) {
        try {
            var data = JSON.parse(e.data);
            if (data.error) return;
            if (data.heartbeat) return;

            currentState = data;
            isWaiting = data.waiting_for_human === true;
            renderAll(data);
        } catch (err) {
            console.error('SSE error:', err);
        }
    };
    es.onerror = function() {
        es.close();
        setTimeout(connectSSE, 2000);
    };
}

// ── Render ──────────────────────────────────────────────

function renderAll(state) {
    if (!state) return;

    // Update counter
    var badge = document.getElementById('qCounter');
    badge.textContent = '剩余 ' + (state.remaining || 0) + ' 次';
    if (state.remaining <= 5) badge.style.color = '#ff6b6b';
    if (state.phase === 'over') badge.textContent = '游戏结束';

    // Update input bar
    var inputBar = document.getElementById('inputBar');
    var input = document.getElementById('msgInput');
    if (state.phase === 'over') {
        inputBar.style.display = 'none';
    } else if (state.phase === 'judging') {
        inputBar.style.display = 'flex';
        input.placeholder = '输入你的完整推理…';
        input.style.flex = '1';
    } else if (isWaiting) {
        inputBar.style.display = 'flex';
        input.placeholder = '输入你的问题…（或输入「提交」结束游戏）';
        input.focus();
    } else {
        inputBar.style.display = 'flex';
        input.disabled = true;
        input.placeholder = '等待裁判回复…';
    }
    if (state.phase !== 'over' && !isWaiting) {
        input.disabled = true;
    } else if (state.phase !== 'over') {
        input.disabled = false;
    }

    // Render chat
    var inner = document.getElementById('chatInner');
    var events = state.events || [];
    for (var i = 0; i < events.length; i++) {
        if (events[i].generation <= lastEventGen) continue;
        lastEventGen = events[i].generation;
        var div = document.createElement('div');
        div.className = 'chat-item ' + (events[i].type || 'system');
        div.textContent = events[i].text || '';
        inner.appendChild(div);
    }

    // Scroll
    var area = document.getElementById('chatArea');
    if (area) area.scrollTop = area.scrollHeight;
}

// ── Actions ────────────────────────────────────────────

function sendDecision(value) {
    if (!value.trim()) return;
    document.getElementById('msgInput').value = '';
    document.getElementById('msgInput').disabled = true;
    fetch('./api/decision', {
        method: 'POST',
        body: new URLSearchParams({ value: value.trim() })
    });
}

document.getElementById('msgSend').addEventListener('click', function() {
    sendDecision(document.getElementById('msgInput').value);
});

document.getElementById('msgInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') sendDecision(this.value);
});

document.getElementById('btnExit').addEventListener('click', function() {
    if (!confirm('确定退出？')) return;
    fetch('./api/stop', { method: 'POST' });
    window.location.href = './';
});

// ── Init ────────────────────────────────────────────────
connectSSE();
