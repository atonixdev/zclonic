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
      chat.classList.toggle('open');
      chat.setAttribute('aria-hidden', chat.classList.contains('open') ? 'false' : 'true');
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
});
