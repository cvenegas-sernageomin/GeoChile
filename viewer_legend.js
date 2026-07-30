// Modal de leyenda con zoom (rueda + doble click) y pan (arrastre). Escritorio.
(function(){
  const modal=document.getElementById('legmodal');
  const img=document.getElementById('legimg');
  const close=document.getElementById('legclose');
  let scale=1, tx=0, ty=0, dragging=false, lx=0, ly=0;
  function apply(){ img.style.transform=`translate(${tx}px,${ty}px) scale(${scale})`; }
  window.abrirLeyenda=function(src){
    img.src=src; scale=1; tx=0; ty=0; apply(); modal.classList.add('open');
  };
  function cerrar(){ modal.classList.remove('open'); img.src=''; }
  close.addEventListener('click',cerrar);
  modal.addEventListener('click',e=>{ if(e.target===modal) cerrar(); });
  img.addEventListener('wheel',e=>{
    e.preventDefault();
    const f=e.deltaY<0?1.15:1/1.15;
    scale=Math.min(8,Math.max(0.2,scale*f)); apply();
  },{passive:false});
  img.addEventListener('dblclick',e=>{ e.preventDefault(); scale=scale>1?1:2; tx=0; ty=0; apply(); });
  img.addEventListener('pointerdown',e=>{ dragging=true; lx=e.clientX; ly=e.clientY;
    try{img.setPointerCapture(e.pointerId);}catch(_){} });
  img.addEventListener('pointermove',e=>{ if(!dragging) return;
    tx+=e.clientX-lx; ty+=e.clientY-ly; lx=e.clientX; ly=e.clientY; apply(); });
  img.addEventListener('pointerup',()=>{ dragging=false; });
  img.addEventListener('pointercancel',()=>{ dragging=false; });
})();
