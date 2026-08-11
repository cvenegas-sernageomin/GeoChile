// Modal de leyenda con zoom y desplazamiento.
// PC: rueda del mouse, doble click y arrastre.  Telefono: pellizco, doble toque y arrastre.
(function(){
  const modal=document.getElementById('legmodal');
  const img=document.getElementById('legimg');
  const close=document.getElementById('legclose');
  const MIN=0.2, MAX=8;
  let scale=1, tx=0, ty=0;

  function apply(){ img.style.transform=`translate(${tx}px,${ty}px) scale(${scale})`; }
  function clamp(s){ return Math.min(MAX, Math.max(MIN, s)); }

  window.abrirLeyenda=function(src){
    img.src=src; scale=1; tx=0; ty=0; apply(); modal.classList.add('open');
  };
  function cerrar(){ modal.classList.remove('open'); img.src=''; pts.clear(); pinchIni=0; }
  close.addEventListener('click',e=>{ e.stopPropagation(); cerrar(); });
  modal.addEventListener('click',e=>{ if(e.target===modal) cerrar(); });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape') cerrar(); });

  img.addEventListener('wheel',e=>{
    e.preventDefault();
    scale=clamp(scale*(e.deltaY<0?1.15:1/1.15)); apply();
  },{passive:false});

  img.addEventListener('dblclick',e=>{ e.preventDefault(); scale=scale>1?1:2; tx=0; ty=0; apply(); });

  /* --- Punteros: 1 = arrastrar, 2 = pellizcar --- */
  const pts=new Map();
  let pinchIni=0, escalaIni=1;

  img.addEventListener('pointerdown',e=>{
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    // setPointerCapture puede lanzar NotFoundError (rarezas de Safari iOS): nunca debe
    // tumbar el gesto, y va DESPUES del set para no perder el puntero si falla.
    try{ img.setPointerCapture(e.pointerId); }catch(_){}
    if(pts.size===2){
      const [a,b]=[...pts.values()];
      pinchIni=Math.hypot(b.x-a.x,b.y-a.y); escalaIni=scale;
    }
  });

  img.addEventListener('pointermove',e=>{
    const prev=pts.get(e.pointerId);
    if(!prev) return;
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pts.size>=2 && pinchIni>0){
      const [a,b]=[...pts.values()];
      const d=Math.hypot(b.x-a.x,b.y-a.y);
      if(d>0){ scale=clamp(escalaIni*(d/pinchIni)); apply(); }
    }else if(pts.size===1){
      tx+=e.clientX-prev.x; ty+=e.clientY-prev.y; apply();
    }
  });

  function soltar(e){
    pts.delete(e.pointerId);
    if(pts.size<2) pinchIni=0;          // al soltar un dedo se termina el pellizco
  }
  img.addEventListener('pointerup',soltar);
  img.addEventListener('pointercancel',soltar);
})();
