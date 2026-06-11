// === 谁是卧底 — SSE Client (Chat UI) ===

var currentState = null;
var roleShown = false;
var lastPhase = null;
var lastEventGen = 0;
var pendingDecision = null;
var currentDecisionType = null;
var selectedVoteId = null;

// ── SSE ─────────────────────────────────────────────────

function connectSSE() {
    var es = new EventSource('./api/stream');
    es.onmessage = function(e) {
        try {
            var data = JSON.parse(e.data);
            if (data.error) return;
            if (data.heartbeat) return;

            // Always update current state for rendering
            currentState = data;

            if (data.waiting_for_human) {
                pendingDecision = data;
                // Show role overlay first if not yet shown
                if (!roleShown && data.civilian_word) {
                    showInfoOverlay(data);
                    roleShown = true;
                }
                // Show decision UI only after overlay is dismissed
                var overlay = document.getElementById('infoOverlay');
                if (!overlay || overlay.style.display === 'none') {
                    showDecision(data);
                }
                return;
            }

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
    if (!state || !state.players) return;

    // Reset on new game
    if (state.phase === 'setup' && lastPhase === 'over') {
        roleShown = false;
        lastEventGen = 0;
        document.getElementById('infoOverlay').style.display = 'none';
        document.getElementById('chatInner').innerHTML = '';
    }
    lastPhase = state.phase;

    updateTopbar(state);
    renderPlayerStrip(state);
    renderChat(state);

    // Show role info once
    if (!roleShown && state.phase !== 'setup' && state.civilian_word) {
        showInfoOverlay(state);
        roleShown = true;
    }

    // Scroll chat to bottom
    var area = document.getElementById('chatArea');
    if (area) area.scrollTop = area.scrollHeight;
}

function updateTopbar(state) {
    var phases = { 'setup':'准备中', 'describing':'描述阶段', 'voting':'投票阶段', 'result':'结果', 'over':'游戏结束' };
    document.getElementById('roundBadge').textContent = '第 ' + state.round_num + ' 轮 · ' + (phases[state.phase] || '');
}

function renderPlayerStrip(state) {
    var strip = document.getElementById('playerStrip');
    strip.innerHTML = '';
    var hasHuman = state.players.some(function(p) { return p.is_human; });

    state.players.forEach(function(p) {
        var card = document.createElement('div');
        card.className = 'strip-card';
        if (!p.alive) card.classList.add('eliminated');
        if (p.is_human) card.classList.add('human-card');
        if (p.description === null && p.alive && state.phase === 'describing') card.classList.add('thinking');

        var extra = '';
        // Spectate: show word + role for everyone; Play: show only own word (no role)
        if (!hasHuman) {
            var roleLabel = p.role === 'spy' ? '🕵卧底' : '👤平民';
            extra = '<div style="font-size:0.6rem;color:var(--text-muted);margin-top:1px;">「' + (p.word || '?') + '」</div>' +
                    '<div style="font-size:0.56rem;color:' + (p.role === 'spy' ? 'var(--spy)' : 'var(--text-muted)') + ';">' + roleLabel + '</div>';
        } else if (p.is_human) {
            extra = '<div style="font-size:0.6rem;color:var(--text-muted);margin-top:1px;">「' + (p.word || '?') + '」</div>';
        }
        // Show badges when eliminated
        var badge = '';
        if (!p.alive) {
            badge = p.role === 'spy'
                ? '<div style="font-size:0.56rem;padding:1px 6px;border-radius:10px;background:var(--spy);color:#fff;display:inline-block;margin-top:2px;">卧底</div>'
                : '<div style="font-size:0.56rem;padding:1px 6px;border-radius:10px;background:#444;color:#999;display:inline-block;margin-top:2px;">淘汰</div>';
        }

        card.innerHTML =
            '<div class="strip-num">' + (p.avatar || '') + '</div>' +
            '<div style="font-size:0.68rem;">' + (p.name || '?') + '</div>' +
            extra + badge;
        strip.appendChild(card);
    });
}

function renderChat(state) {
    var inner = document.getElementById('chatInner');
    var events = state.events || [];

    for (var i = 0; i < events.length; i++) {
        var ev = events[i];
        var gen = ev.generation || 0;
        if (gen <= lastEventGen) continue;
        lastEventGen = gen;

        var el = createChatElement(ev, state);
        if (el) inner.appendChild(el);

        // If it's a tally event, render vote results
        if (ev.type === 'tally' && ev.text) {
            try {
                var tally = JSON.parse(ev.text);
                var tallyEl = document.createElement('div');
                tallyEl.className = 'chat-tally';
                var parts = [];
                for (var pid in tally) {
                    var p = state.players.find(function(pp) { return pp.id === parseInt(pid); });
                    parts.push((p ? p.name : pid + '号') + '：' + tally[pid] + '票');
                }
                tallyEl.textContent = '📊 ' + parts.join('  ');
                inner.appendChild(tallyEl);
            } catch(e) {}
        }
    }
}

function createChatElement(ev, state) {
    var div = document.createElement('div');

    // System / phase messages
    if (ev.type === 'phase' || ev.type === 'system') {
        div.className = 'chat-system';
        if (ev.text && ev.text.indexOf('淘汰') >= 0) div.classList.add('eliminate');
        if (ev.type === 'game_over') div.classList.add('game_over');
        div.textContent = ev.text || '';
        return div;
    }

    if (ev.type === 'game_over') {
        div.className = 'chat-system game_over';
        div.textContent = ev.text || '';
        return div;
    }

    // Description bubble
    if (ev.type === 'description') {
        var player = state.players.find(function(p) { return p.id === ev.player_id; });
        div.className = 'chat-bubble';
        div.innerHTML =
            '<div class="chat-avatar">' + (player ? player.avatar : '?') + '</div>' +
            '<div class="chat-body">' +
            '<div class="chat-name">' + (player ? player.name : '?') + '</div>' +
            '<div class="chat-msg">' + (ev.text || '') + '</div>' +
            '</div>';
        return div;
    }

    // Vote event
    if (ev.type === 'vote') {
        div.className = 'chat-vote';
        div.textContent = ev.text || '';
        return div;
    }

    // Eliminate
    if (ev.type === 'eliminate') {
        div.className = 'chat-system eliminate';
        div.textContent = '⚡ ' + (ev.text || '');
        return div;
    }

    // Waiting message (skip — just for backend)
    if (ev.type === 'waiting' || ev.type === 'describe_turn' || ev.type === 'vote_turn') {
        return null;
    }

    // Default
    div.className = 'chat-system';
    div.textContent = ev.text || '';
    return div;
}

// ── Decision UI ─────────────────────────────────────────

function showDecision(ctx) {
    // 同一类型的决策已经显示中，不重复重建（防止冲掉用户已选内容）
    if (currentDecisionType === ctx.type) return;
    hideInputs();
    currentDecisionType = ctx.type;

    if (ctx.type === 'describe') {
        document.getElementById('inputBar').style.display = 'flex';
        document.getElementById('msgInput').value = '';
        document.getElementById('msgInput').focus();
    } else if (ctx.type === 'vote') {
        document.getElementById('voteBar').style.display = 'flex';
        var opts = document.getElementById('voteOptions');
        opts.innerHTML = '';
        selectedVoteId = null;
        document.getElementById('voteConfirm').disabled = true;

        (ctx.alive_ids || []).forEach(function(id) {
            var p = currentState.players.find(function(pp) { return pp.id === parseInt(id); });
            var chip = document.createElement('button');
            chip.className = 'vote-chip';
            chip.textContent = (p ? p.avatar + ' ' + p.name : id);
            chip.onclick = function() {
                document.querySelectorAll('.vote-chip').forEach(function(c) { c.classList.remove('selected'); });
                chip.classList.add('selected');
                selectedVoteId = id;
                document.getElementById('voteConfirm').disabled = false;
            };
            opts.appendChild(chip);
        });
    }
}

function hideInputs() {
    document.getElementById('inputBar').style.display = 'none';
    document.getElementById('voteBar').style.display = 'none';
    document.getElementById('msgInput').value = '';
    selectedVoteId = null;
    currentDecisionType = null;
}

// ── Info Overlay ────────────────────────────────────────

function showInfoOverlay(state) {
    var hasHuman = state.players.some(function(p) { return p.is_human; });
    var overlay = document.getElementById('infoOverlay');
    var card = document.getElementById('infoCard');
    var spy = state.players.find(function(p) { return p.role === 'spy'; });

    if (hasHuman) {
        // Human player: show only word, NOT the role (no one knows who the spy is)
        var me = state.players.find(function(p) { return p.is_human; });
        var myWord = me ? me.word : state.civilian_word;
        card.innerHTML =
            '<h2>你的词语</h2>' +
            '<div class="word-text" style="font-size:1.4rem;margin:12px 0;">「' + myWord + '」</div>' +
            '<p style="font-size:0.8rem;color:var(--text-muted);">用一句话描述它，注意不要直接说出来</p>' +
            '<p style="font-size:0.75rem;color:var(--text-muted);">可能有人拿到了不同的词…</p>' +
            '<button onclick="dismissOverlay()">知道了</button>';
    } else {
        // Spectate: info is shown in the player strip, just show a brief tip
        card.innerHTML =
            '<h2>👁️ 观战模式</h2>' +
            '<p style="font-size:0.85rem;color:var(--text-secondary);">每个玩家下方标注了词语和身份</p>' +
            '<p style="font-size:0.8rem;color:var(--text-muted);">平民词「' + state.civilian_word + '」 · 卧底词「' + state.spy_word + '」</p>' +
            '<button onclick="dismissOverlay()">开始围观</button>';
    }
    overlay.style.display = '';
}

function dismissOverlay() {
    document.getElementById('infoOverlay').style.display = 'none';
    // If there's a pending decision waiting, show it now
    if (pendingDecision) {
        showDecision(pendingDecision);
    }
}

// ── Human Actions ───────────────────────────────────────

document.getElementById('msgSend').addEventListener('click', function() {
    var text = document.getElementById('msgInput').value.trim();
    if (!text) return;
    hideInputs();
    fetch('./api/decision', {
        method: 'POST',
        body: new URLSearchParams({ decision_id: 'describe', value: text })
    });
});

document.getElementById('msgInput').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('msgSend').click();
});

document.getElementById('voteConfirm').addEventListener('click', function() {
    var vid = selectedVoteId;
    console.log('submitVote called, selectedVoteId=', vid, 'type=', typeof vid);
    if (!vid || vid === 'null' || vid === 'undefined') {
        console.warn('Invalid vote id, ignoring');
        return;
    }
    hideInputs();
    var body = new URLSearchParams();
    body.append('decision_id', 'vote');
    body.append('value', String(vid));
    console.log('Sending vote:', String(vid));
    fetch('./api/decision', { method: 'POST', body: body });
});

// ── Exit ────────────────────────────────────────────────

document.getElementById('btnExit').addEventListener('click', function() {
    if (!confirm('确定退出？')) return;
    fetch('./api/stop', { method: 'POST' });
    window.location.href = './';
});

// ── Init ────────────────────────────────────────────────
connectSSE();
