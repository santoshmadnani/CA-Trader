
(function(){
  // 1) Ripple ink effect on buttons/tabs/cards you click
  document.addEventListener('click', function(e){
    const target = e.target.closest('button,.btn,.icon-btn,.tf-btn,.theme-btn,.add-btn,.ca-ai-btn,.mobile-menu-btn');
    if(!target) return;
    const rect = target.getBoundingClientRect();
    const ink = document.createElement('span');
    const size = Math.max(rect.width, rect.height);
    ink.className = 'ripple-ink';
    ink.style.width = ink.style.height = size + 'px';
    ink.style.left = (e.clientX - rect.left - size/2) + 'px';
    ink.style.top = (e.clientY - rect.top - size/2) + 'px';
    target.appendChild(ink);
    setTimeout(()=>ink.remove(), 600);
  }, true);

  // 2) Flash green/red on any element whose numeric text content changes (LTP, price cells etc.)
  const watchSelectors = '.wl-item .price, .wl-price, [class*="ltp"], .metric .value, .stat-card .value';
  let lastValues = new WeakMap();
  function checkFlash(){
    document.querySelectorAll(watchSelectors).forEach(el=>{
      const txt = el.textContent.trim();
      const num = parseFloat(txt.replace(/[^0-9.\-]/g,''));
      if(isNaN(num)) return;
      const prev = lastValues.get(el);
      if(prev !== undefined && prev !== num){
        el.classList.remove('flash-up','flash-down');
        void el.offsetWidth; // restart animation
        el.classList.add(num > prev ? 'flash-up' : 'flash-down');
      }
      lastValues.set(el, num);
    });
  }
  setInterval(checkFlash, 1500);

  // 3) Gentle fade-in for panels/tabs when they become active (covers dynamically toggled ones too)
  const panelObserver = new MutationObserver(muts=>{
    muts.forEach(m=>{
      if(m.type === 'attributes' && m.target.classList && m.target.classList.contains('active')){
        m.target.style.animation = 'none';
        void m.target.offsetWidth;
        m.target.style.animation = '';
      }
    });
  });
  document.querySelectorAll('.panel,.tab-panel').forEach(p=>{
    panelObserver.observe(p, { attributes:true, attributeFilter:['class'] });
  });

  // 4) Toast pop animation hook (works with existing toast/notification elements if class 'toast' or 'notification-menu' is used)
  const toastObserver = new MutationObserver(muts=>{
    muts.forEach(m=>{
      m.addedNodes && m.addedNodes.forEach(n=>{
        if(n.nodeType===1 && (n.classList?.contains('toast') || n.classList?.contains('notification-item'))){
          n.style.animation = 'toastPop .35s cubic-bezier(.2,.9,.3,1.2) both';
        }
      });
    });
  });
  toastObserver.observe(document.body, { childList:true, subtree:true });
})();

  // Harden mobile drawer state after orientation/resize.
  window.addEventListener('resize',()=>{
    if(window.innerWidth>760){
      document.querySelector('.sidebar')?.classList.remove('mobile-open');
      document.body.style.overflow='';
    }
  });
  // Make the chart a gesture surface so iOS does not start long-press text selection.
  const chartSurface=document.getElementById('chartViewport');
  if(chartSurface){
    chartSurface.style.webkitUserSelect='none';
    chartSurface.style.userSelect='none';
    chartSurface.style.webkitTouchCallout='none';
  }
