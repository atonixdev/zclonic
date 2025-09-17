// static/js/main.js
// Small script to toggle mobile navigation

document.addEventListener('DOMContentLoaded', function(){
  const btn = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.primary-nav');
  if(btn && nav){
    btn.addEventListener('click', function(){
      const expanded = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!expanded));
      nav.classList.toggle('open');
    });
  }

  // Theme toggle
  const themeBtn = document.querySelector('.theme-toggle');
  const root = document.documentElement;
  function setTheme(t){
    if(t === 'light'){
      document.body.classList.add('theme-light');
      themeBtn && (themeBtn.textContent = '☀️');
      themeBtn && themeBtn.setAttribute('aria-pressed','true');
    } else {
      document.body.classList.remove('theme-light');
      themeBtn && (themeBtn.textContent = '🌙');
      themeBtn && themeBtn.setAttribute('aria-pressed','false');
    }
    try{ localStorage.setItem('theme', t); }catch(e){}
  }

  // initialize
  try{
    const stored = localStorage.getItem('theme');
    setTheme(stored === 'light' ? 'light' : 'dark');
  }catch(e){ setTheme('dark') }

  if(themeBtn){
    themeBtn.addEventListener('click', function(){
      const isLight = document.body.classList.contains('theme-light');
      setTheme(isLight ? 'dark' : 'light');
    });
  }

  // Translation loader
  const langSelect = document.querySelector('.lang-select');
  async function loadLocale(lang){
    try{
      const res = await fetch('/static/locales/' + lang + '.json');
      const data = await res.json();
      applyTranslations(data);
      try{ localStorage.setItem('lang', lang); }catch(e){}
    }catch(e){ console.warn('Failed to load locale', e) }
  }

  function applyTranslations(dict){
    document.querySelectorAll('[data-i18n]').forEach(function(el){
      const key = el.getAttribute('data-i18n');
      if(dict[key]) el.textContent = dict[key];
    });
    // buttons/links by class
    const btnPrimary = document.querySelector('.btn-primary');
    const btnSecondary = document.querySelector('.btn-secondary');
    const uploadBtn = document.querySelector('.cta-group .btn');
    if(btnPrimary && dict['get_started']) btnPrimary.textContent = dict['get_started'];
    if(btnSecondary && dict['learn_more']) btnSecondary.textContent = dict['learn_more'];
    if(uploadBtn && dict['upload_data']) uploadBtn.textContent = dict['upload_data'];
  }

  // Initialize language
  try{
    const storedLang = localStorage.getItem('lang') || 'en';
    if(langSelect) langSelect.value = storedLang;
    loadLocale(storedLang);
  }catch(e){ loadLocale('en') }

  if(langSelect){
    langSelect.addEventListener('change', function(e){
      loadLocale(e.target.value);
    });
  }

  // Chat widget
  const chat = document.getElementById('ai-chat');
  const chatToggle = document.querySelector('.ai-chat-toggle');
  const chatClose = document.querySelector('.ai-chat-close');
  const chatForm = document.getElementById('ai-chat-form');
  const chatBody = document.getElementById('ai-chat-body');
  const chatInput = document.getElementById('ai-input');

  function appendMessage(text, who){
    const el = document.createElement('div');
    el.className = 'message ' + (who === 'user' ? 'user' : 'bot');
    el.textContent = text;
    chatBody.appendChild(el);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  if(chatToggle && chat){
    chatToggle.addEventListener('click', function(){
      const opening = !chat.classList.contains('open');
      chat.classList.toggle('open');
      chat.setAttribute('aria-hidden', chat.classList.contains('open') ? 'false' : 'true');
      if(opening){
        chat.classList.add('pop');
        setTimeout(()=>chat.classList.remove('pop'), 800);
      }
    });
  }

  if(chatClose && chat){
    chatClose.addEventListener('click', function(){
      chat.classList.remove('open');
      chat.setAttribute('aria-hidden', 'true');
    });
  }

  if(chatForm){
    chatForm.addEventListener('submit', function(e){
      e.preventDefault();
      const q = (chatInput && chatInput.value && chatInput.value.trim());
      if(!q) return;
      appendMessage(q, 'user');
      chatInput.value = '';
      // Send to server API
      appendMessage('…', 'bot');
      fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: q, model: 'mock'})
      }).then(function(res){
        return res.json();
      }).then(function(data){
        // remove the loading placeholder (last bot message)
        const msgs = chatBody.querySelectorAll('.message.bot');
        if(msgs.length) msgs[msgs.length-1].textContent = data.reply || '(no reply)';
      }).catch(function(err){
        const msgs = chatBody.querySelectorAll('.message.bot');
        if(msgs.length) msgs[msgs.length-1].textContent = '(error) ' + err;
      });
    });
  }

  // In-dashboard AI Assistant (right column) - only present on dashboard for logged-in users
  const assistantForm = document.getElementById('assistant-form');
  const assistantInput = document.getElementById('assistant-input');
  const assistantMessages = document.getElementById('assistant-messages');

  function assistantAppend(text, who){
    if(!assistantMessages) return;
    const el = document.createElement('div');
    el.className = 'assistant-message ' + (who === 'user' ? 'user' : 'bot');
    el.style.padding = '0.55rem';
    el.style.borderRadius = '8px';
    el.style.marginBottom = '0.5rem';
    el.style.background = who === 'user' ? 'linear-gradient(90deg, rgba(124,92,255,0.12), rgba(0,194,168,0.06))' : 'rgba(255,255,255,0.02)';
    el.textContent = text;
    assistantMessages.appendChild(el);
    assistantMessages.scrollTop = assistantMessages.scrollHeight;
  }

  if(assistantForm){
    assistantForm.addEventListener('submit', function(e){
      e.preventDefault();
      const q = (assistantInput && assistantInput.value && assistantInput.value.trim());
      if(!q) return;
      assistantAppend(q, 'user');
      assistantInput.value = '';
      assistantAppend('\u2026', 'bot');
      fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: q, model: 'mock'})
      }).then(res=>res.json()).then(data=>{
        // replace last bot placeholder
        const bots = assistantMessages.querySelectorAll('.assistant-message.bot');
        if(bots.length) bots[bots.length-1].textContent = data.reply || '(no reply)';
      }).catch(err=>{
        const bots = assistantMessages.querySelectorAll('.assistant-message.bot');
        if(bots.length) bots[bots.length-1].textContent = '(error) ' + err;
      });
    });
  }

  // Dashboard terminal handling (safe whitelist on server)
  const terminalForm = document.getElementById('terminal-form');
  const terminalInput = document.getElementById('terminal-input');
  const terminalOutput = document.getElementById('terminal-output');

  function terminalAppend(text, cls){
    if(!terminalOutput) return;
    const el = document.createElement('pre');
    el.style.whiteSpace = 'pre-wrap';
    el.style.margin = '0 0 0.5rem 0';
    el.textContent = text;
    if(cls === 'err') el.style.color = 'var(--accent-2)';
    terminalOutput.appendChild(el);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  if(terminalForm){
    terminalForm.addEventListener('submit', function(e){
      e.preventDefault();
      const cmd = (terminalInput && terminalInput.value && terminalInput.value.trim());
      if(!cmd) return;
      terminalAppend('$ ' + cmd);
      terminalInput.value = '';
      terminalAppend('…');
      fetch('/api/exec', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({cmd: cmd})
      }).then(res=>res.json()).then(data=>{
        // remove last placeholder if it's the ellipsis
        const last = terminalOutput.lastChild;
        if(last && last.textContent === '…') last.remove();
        if(data.error){
          terminalAppend('Error: ' + data.error, 'err');
          return;
        }
        if(data.stdout) terminalAppend(data.stdout);
        if(data.stderr) terminalAppend('ERR: ' + data.stderr, 'err');
        if(typeof data.returncode !== 'undefined') terminalAppend('\n(return code: ' + data.returncode + ')');
      }).catch(err=>{
        terminalAppend('Request error: ' + err, 'err');
      });
    });
  }

  // Password visibility toggles
  document.querySelectorAll('.toggle-password').forEach(function(btn){
    btn.addEventListener('click', function(e){
      var targetId = btn.getAttribute('data-target');
      var input = document.getElementById(targetId);
      if(!input) return;
      if(input.type === 'password'){
        input.type = 'text';
        btn.textContent = '🙈';
      } else {
        input.type = 'password';
        btn.textContent = '👁️';
      }
    });
  });

  // Signup confirm-password validation
  var signupForm = document.querySelector('form[action="/signup"]');
  if(signupForm){
    signupForm.addEventListener('submit', function(e){
      var pw = document.getElementById('password');
      var cpw = document.getElementById('confirm_password');
      // remove existing inline error
      var existing = signupForm.querySelector('.pw-error');
      if(existing) existing.remove();
      if(pw && cpw && pw.value !== cpw.value){
        e.preventDefault();
        var err = document.createElement('div');
        err.className = 'pw-error';
        err.style.color = 'var(--accent-2)';
        err.style.marginTop = '0.5rem';
        err.textContent = 'Passwords do not match';
        cpw.parentNode.appendChild(err);
        cpw.focus();
        return false;
      }
    });
  }

  // Account page: create API token via AJAX
  const createTokenBtn = document.getElementById('create-token-btn');
  const newTokenNameInput = document.getElementById('new-token-name');
  const newTokenOutput = document.getElementById('new-token-output');
  const newTokenValue = document.getElementById('new-token-value');
  if(createTokenBtn){
    createTokenBtn.addEventListener('click', function(e){
      e.preventDefault();
      const name = (newTokenNameInput && newTokenNameInput.value && newTokenNameInput.value.trim()) || 'token';
      createTokenBtn.disabled = true;
      fetch('/api/create-token', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name})
      }).then(res=>res.json()).then(data=>{
        createTokenBtn.disabled = false;
        if(data.error){
          alert('Error: ' + data.error);
          return;
        }
        if(newTokenOutput && newTokenValue){
          newTokenValue.textContent = data.token || '';
          newTokenOutput.style.display = 'block';
        }
      }).catch(err=>{
        createTokenBtn.disabled = false;
        alert('Request failed: ' + err);
      });
    });
  }

  // Copy newly created token to clipboard
  const copyTokenBtn = document.getElementById('copy-token-btn');
  if(copyTokenBtn){
    copyTokenBtn.addEventListener('click', function(e){
      e.preventDefault();
      if(!newTokenValue) return;
      const text = newTokenValue.textContent || '';
      navigator.clipboard.writeText(text).then(()=>{
        copyTokenBtn.textContent = 'Copied';
        setTimeout(()=>copyTokenBtn.textContent = 'Copy', 1800);
      }).catch(()=>alert('Copy failed'));
    });
  }

  // Revoke token handlers
  document.querySelectorAll('.revoke-token').forEach(function(btn){
    btn.addEventListener('click', function(e){
      e.preventDefault();
      const id = btn.getAttribute('data-token-id');
      if(!id) return;
      if(!confirm('Revoke this token?')) return;
      fetch('/api/revoke-token', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token_id: id})
      }).then(res=>res.json()).then(data=>{
        if(data.error){ alert('Error: ' + data.error); return; }
        // remove or mark revoked
        btn.disabled = true;
        btn.textContent = 'Revoked';
        btn.parentNode.innerHTML = '<span class="muted">Revoked</span>';
      }).catch(err=>{ alert('Request failed: ' + err); });
    });
  });
});
