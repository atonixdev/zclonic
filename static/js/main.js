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
});
