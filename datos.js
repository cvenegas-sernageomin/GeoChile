/* Datos puntuales de las GDB (geocronología, fósiles, yacimientos, estructuras) con filtros.
   Lee datos/index.json (generado por tools/exportar_gdb_a_datos.py) y construye la interfaz sola:
   cada tipo trae sus filtros (multi / rango / texto). Usa globals del visor: map, L, PANE_GIRA, panel, togglePanel. */
(function(){
'use strict';
const DATA_V='?v=20261015';   // subir al regenerar datos/ (el service worker los guarda con caché primero)
const COLORES=['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#008b8b','#9a6324','#800000','#808000','#000075','#f032e6','#2a9d8f','#bcbd22','#7f7f7f'];
const ICONO={geocronologia:'⏳',fosiles:'🦴',yacimientos:'⛏️',estructuras:'📐'};
const RADIO={geocronologia:6,fosiles:6,yacimientos:5,estructuras:4};
const MAX_TABLA=400;
const fmt=n=>n.toLocaleString('es-CL');
const norm=s=>String(s==null?'':s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();
const el=(t,c,txt)=>{const e=document.createElement(t); if(c) e.className=c; if(txt!=null) e.textContent=txt; return e;};
const sec=document.getElementById('datos');
if(!sec||typeof map==='undefined') return;

const css=document.createElement('style');
css.textContent=`
#datos{column-span:all}
#datos>details>summary{font-size:15px}
.dtipo summary{display:flex;align-items:center;gap:6px}
.dbody{padding:8px 10px 10px;border-top:1px solid #eef2f6}
.dchk{display:flex;align-items:center;gap:8px;font-weight:600;color:#1a5276;font-size:14px;cursor:pointer}
.dchk input{width:19px;height:19px;accent-color:#1a5276;margin:0}
.dfil{margin-top:8px;display:none}
.dfil.on{display:block}
.dgrp{margin:8px 0}
.dgrp>b{display:block;font-size:12px;color:#475569;margin-bottom:3px}
.dchips{display:flex;flex-wrap:wrap;gap:5px;max-height:104px;overflow-y:auto}
.dchip{display:inline-flex;align-items:center;gap:4px;border:1px solid #cbd5e1;background:#fff;border-radius:999px;padding:3px 9px;font-size:12.5px;cursor:pointer;user-select:none}
.dchip.on{background:#1a5276;border-color:#1a5276;color:#fff}
.dchip input{display:none}
.dchip small{opacity:.7}
.drango{display:flex;align-items:center;gap:6px;font-size:13px}
.drango input,.dtxt{font-size:14px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:8px;box-sizing:border-box}
.drango input{width:88px}
.dtxt{width:100%}
.dcount{font-weight:700;color:#1a5276;font-size:14px;margin:8px 0 4px}
.dleg{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:12px;color:#334155;margin-bottom:6px}
.dleg i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;border:1px solid #222}
.dbtns{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.dbtns button{font-size:13px;border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:7px 11px;cursor:pointer}
.dbtns label{font-size:13px;display:flex;align-items:center;gap:5px;cursor:pointer}
.dpop{font-size:13px;line-height:1.35;min-width:230px;max-width:300px}
.dpop h4{margin:0 0 4px;font-size:14px;color:#1a5276}
.dpop table{border-collapse:collapse;width:100%}
.dpop td{padding:2px 4px 2px 0;vertical-align:top;border-bottom:1px solid #eef2f6}
.dpop td:first-child{color:#64748b;white-space:nowrap}
.dpop .fte{margin-top:6px;font-size:11.5px;color:#64748b}
.dpop a{color:#1a5276;font-weight:600}
#dresumen{background:rgba(255,255,255,.93);border-radius:8px;padding:5px 9px;font-size:12.5px;box-shadow:0 1px 4px rgba(0,0,0,.3);display:none;max-width:260px}
#dresumen.on{display:block}
#dtabla{max-width:min(1100px,calc(100% - 20px));width:calc(100% - 20px);padding:12px}
#dtabla .tw{max-height:62vh;overflow:auto}
#dtabla table{border-collapse:collapse;font-size:12.5px;width:100%}
#dtabla th{position:sticky;top:0;background:#1a5276;color:#fff;text-align:left;padding:5px 7px;white-space:nowrap}
#dtabla td{padding:4px 7px;border-bottom:1px solid #e2e8f0;white-space:nowrap}
#dtabla tr.f{cursor:pointer}
#dtabla tr.f:hover td{background:#eaf2f8}
`;
document.head.appendChild(css);

let INDEX=null, PDF_GB={};
const T={};   // tipo -> estado
map.createPane('pane_datos',PANE_GIRA).style.zIndex=450;   // sobre grilla (400) y overlays
const resumen=L.control({position:'bottomleft'});
resumen.onAdd=()=>{const d=el('div'); d.id='dresumen'; L.DomEvent.disableClickPropagation(d); return d;};
resumen.addTo(map);

function pintarResumen(){
  const d=document.getElementById('dresumen'); if(!d) return;
  const act=Object.values(T).filter(t=>t.on&&t.sel);
  d.classList.toggle('on',act.length>0);
  d.replaceChildren(...act.map(t=>el('div',null,`${ICONO[t.id]} ${t.cfg.titulo}: ${fmt(t.sel.length)} de ${fmt(t.d.n)}`)));
}

/* ---- columnas ---- */
function prepararColumnas(t){
  t.col={};
  for(const k of Object.keys(t.d)){
    if(['n','esc','lon','lat','c'].includes(k)) continue;
    const c=t.d[k];
    t.col[k]=Array.isArray(c)?{num:true,v:c}:{num:false,v:c.v,d:c.d,dn:null};
  }
}
const valor=(t,k,i)=>{const c=t.col[k]; if(!c) return null; return c.num?c.v[i]:(c.v[i]<0?null:c.d[c.v[i]]);};
const lon=(t,i)=>t.d.lon[i]/t.d.esc, lat=(t,i)=>t.d.lat[i]/t.d.esc;

/* ---- filtros ---- */
function compilar(t){
  const preds=[];
  for(const f of t.cfg.filtros){
    const c=t.col[f.campo]; if(!c) continue;
    const e=t.fil[f.campo];
    if(f.control==='multi' && e.size){
      const ok=new Set(); c.d.forEach((n,j)=>{ if(e.has(n)) ok.add(j); });
      preds.push(i=>ok.has(c.v[i]));
    }else if(f.control==='rango' && (e.min!=null||e.max!=null)){
      preds.push(i=>{ const x=c.v[i]; return x!=null && (e.min==null||x>=e.min) && (e.max==null||x<=e.max); });
    }else if(f.control==='texto' && e.q){
      const toks=norm(e.q).split(/\s+/).filter(Boolean);
      if(!c.dn) c.dn=c.d.map(norm);
      const ok=c.dn.map(s=>toks.every(w=>s.includes(w)));
      preds.push(i=>c.v[i]>=0 && ok[c.v[i]]);
    }
  }
  if(t.vista.checked){
    const b=map.getBounds();
    preds.push(i=>b.contains([lat(t,i),lon(t,i)]));
  }
  return preds;
}
function aplicar(t){
  const preds=compilar(t), sel=[];
  for(let i=0;i<t.d.n;i++){ let ok=true; for(const p of preds){ if(!p(i)){ok=false;break;} } if(ok) sel.push(i); }
  t.sel=sel; pintar(t); pintarResumen();
}
let debounce={};
const programar=t=>{ clearTimeout(debounce[t.id]); debounce[t.id]=setTimeout(()=>aplicar(t),160); };

/* ---- mapa ---- */
function colorDe(t,i){
  const c=t.col[t.cfg.color_por]; if(!c) return '#444';
  const j=c.v[i]; return j<0?'#999':(t.colores[c.d[j]]||'#999');
}
function pintar(t){
  t.capa.clearLayers();
  const r=RADIO[t.id]||5;
  for(const i of t.sel){
    const m=L.circleMarker([lat(t,i),lon(t,i)],{renderer:t.render,pane:'pane_datos',radius:r,weight:.8,color:'#1b1b1b',
      fillColor:colorDe(t,i),fillOpacity:.88});
    m._i=i; m.on('click',e=>abrirPopup(t,i,e.latlng)); t.capa.addLayer(m);
  }
  t.cuenta.textContent=`${fmt(t.sel.length)} de ${fmt(t.d.n)} puntos`;
  // leyenda de colores con lo que hay en la selección
  const cnt={}, c=t.col[t.cfg.color_por];
  if(c) for(const i of t.sel){ const j=c.v[i]; const n=j<0?'(sin dato)':c.d[j]; cnt[n]=(cnt[n]||0)+1; }
  t.leg.replaceChildren(...Object.entries(cnt).sort((a,b)=>b[1]-a[1]).slice(0,12).map(([n,k])=>{
    const s=el('span'); const i=el('i'); i.style.background=t.colores[n]||'#999'; s.append(i,`${n} (${fmt(k)})`); return s; }));
}
function abrirPopup(t,i,ll){
  const div=el('div','dpop'); div.appendChild(el('h4',null,t.cfg.titulo));
  const tb=el('table');
  for(const [k,et] of t.cfg.popup){
    let v=valor(t,k,i); if(v==null||v==='') continue;
    if(k==='certificado'&&!/^https:\/\//i.test(v)) continue;
    const tr=el('tr'); tr.appendChild(el('td',null,et)); tr.appendChild(el('td',null,String(v))); tb.appendChild(tr);
  }
  div.appendChild(tb);
  const ca=INDEX.cartas[t.d.c[i]];
  if(ca){
    const f=el('div','fte');
    const ti=ca.titulo||'';
    f.append('Carta: '+ti+(ca.anio&&!ti.includes(ca.anio)?` (${ca.anio})`:'')+(ca.gb?` · ${ca.gb}`:'')+'. Datos de la GDB oficial de SERNAGEOMIN. ');
    const pdf=ca.gb&&PDF_GB[ca.gb];
    if(pdf&&(/^https:\/\//i.test(pdf)||/^[\w][\w./-]*$/.test(pdf))){
      const a=el('a',null,'⬇ Informe PDF'); a.href=pdf; a.target='_blank'; a.rel='noopener noreferrer'; f.appendChild(a);
    }
    div.appendChild(f);
  }
  L.popup({maxWidth:320}).setLatLng(ll||[lat(t,i),lon(t,i)]).setContent(div).openOn(map);
}

/* ---- tabla y CSV ---- */
function celda(v){ return v==null?'':String(v); }
function abrirTabla(t){
  let dlg=document.getElementById('dtabla');
  if(!dlg){ dlg=el('dialog','hoja'); dlg.id='dtabla'; document.body.appendChild(dlg); }
  dlg.replaceChildren();
  const campos=t.cfg.popup.map(p=>p[0]).filter(k=>!['observacion','certificado'].includes(k)).slice(0,8);
  let idx=t.sel.slice();
  const ordenar=t.col.edad_ma?'edad_ma':null;
  if(ordenar) idx.sort((a,b)=>(valor(t,ordenar,a)??1e9)-(valor(t,ordenar,b)??1e9));
  const top=el('div'); top.style.cssText='display:flex;align-items:center;gap:10px;margin-bottom:8px';
  const h=el('h2',null,`${t.cfg.titulo} — ${fmt(t.sel.length)} puntos`); h.style.margin='0'; h.style.flex='1';
  const x=el('button','btn','✕ Cerrar'); x.style.cssText='width:auto;margin:0;padding:7px 12px'; x.onclick=()=>dlg.close();
  top.append(h,x); dlg.appendChild(top);
  if(idx.length>MAX_TABLA) dlg.appendChild(el('p',null,`Se muestran los primeros ${MAX_TABLA}${ordenar?' (por edad)':''}. Usa ⬇ CSV para todos.`));
  const tw=el('div','tw'), tb=el('table'), th=el('tr');
  campos.forEach(k=>th.appendChild(el('th',null,t.cfg.popup.find(p=>p[0]===k)[1])));
  tb.appendChild(th);
  idx.slice(0,MAX_TABLA).forEach(i=>{
    const tr=el('tr','f'); campos.forEach(k=>tr.appendChild(el('td',null,celda(valor(t,k,i)))));
    tr.onclick=()=>{ dlg.close(); map.setView([lat(t,i),lon(t,i)],Math.max(map.getZoom(),13)); abrirPopup(t,i); };
    tb.appendChild(tr);
  });
  tw.appendChild(tb); dlg.appendChild(tw); dlg.showModal();
}
function exportarCSV(t){
  const campos=Object.keys(t.col);
  const q=v=>{ const s=celda(v); return /[",\n\r;]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s; };
  const filas=[['lon','lat','carta','informe_gb',...campos].join(',')];
  for(const i of t.sel){
    const ca=INDEX.cartas[t.d.c[i]]||{};
    filas.push([lon(t,i).toFixed(5),lat(t,i).toFixed(5),ca.titulo,ca.gb,...campos.map(k=>valor(t,k,i))].map(q).join(','));
  }
  const blob=new Blob(['﻿'+filas.join('\r\n')],{type:'text/csv;charset=utf-8'});
  const a=el('a'); a.href=URL.createObjectURL(blob); a.download=`geochile_${t.id}.csv`;
  document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href); a.remove();},500);
}

/* ---- interfaz ---- */
function crearFiltros(t,cont){
  t.fil={};
  for(const f of t.cfg.filtros){
    const g=el('div','dgrp'); g.appendChild(el('b',null,f.etiqueta));
    if(f.control==='multi'){
      const sel=t.fil[f.campo]=new Set(), chips=el('div','dchips');
      for(const [v,n] of f.valores){
        const lb=el('label','dchip'), cb=el('input'); cb.type='checkbox';
        lb.append(cb,v+' ',el('small',null,fmt(n)));
        cb.onchange=()=>{ cb.checked?sel.add(v):sel.delete(v); lb.classList.toggle('on',cb.checked); programar(t); };
        chips.appendChild(lb);
      }
      g.appendChild(chips);
    }else if(f.control==='rango'){
      const e=t.fil[f.campo]={min:null,max:null}, w=el('div','drango');
      const a=el('input'), b=el('input'); a.type=b.type='number'; a.step=b.step='any';
      a.placeholder='mín '+f.min; b.placeholder='máx '+f.max; a.setAttribute('aria-label',f.etiqueta+' mínimo'); b.setAttribute('aria-label',f.etiqueta+' máximo');
      const lee=()=>{ e.min=a.value===''?null:+a.value; e.max=b.value===''?null:+b.value; programar(t); };
      a.oninput=b.oninput=lee; w.append(a,'–',b); g.appendChild(w);
    }else{
      const e=t.fil[f.campo]={q:''}, i=el('input','dtxt'); i.type='search'; i.placeholder=f.etiqueta+'…';
      i.oninput=()=>{ e.q=i.value.trim(); programar(t); }; g.appendChild(i);
    }
    cont.appendChild(g);
  }
}
function limpiar(t){
  t.ui.querySelectorAll('input[type=checkbox]:not(.don):not(.dvista)').forEach(c=>{c.checked=false; c.parentElement.classList.remove('on');});
  t.ui.querySelectorAll('.drango input,.dtxt').forEach(i=>{i.value='';});
  for(const f of t.cfg.filtros){ const e=t.fil[f.campo];
    if(f.control==='multi') e.clear(); else if(f.control==='rango'){e.min=e.max=null;} else e.q=''; }
  aplicar(t);
}
async function activar(t,on){
  t.on=on; t.fl.classList.toggle('on',on);
  if(!on){ t.capa.remove(); t.sel=null; pintarResumen(); return; }
  if(!t.d){
    t.cuenta.textContent='Cargando…';
    try{
      const r=await fetch(t.cfg.archivo+DATA_V); if(!r.ok) throw new Error(r.status);
      t.d=await r.json(); prepararColumnas(t);
      const c=t.col[t.cfg.color_por]; t.colores={};
      if(c){ const cnt={}; c.v.forEach(j=>{ if(j>=0) cnt[j]=(cnt[j]||0)+1; });
        Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]).forEach((j,k)=>{ t.colores[c.d[j]]=COLORES[k%COLORES.length]; }); }
    }catch(e){
      t.cuenta.textContent='No se pudo cargar (¿sin señal y sin haberlo abierto antes?)'; t.chk.checked=false; t.on=false; t.fl.classList.remove('on'); return;
    }
  }
  t.capa.addTo(map); aplicar(t);
}
function crearTipo(id,cfg){
  const t=T[id]={id,cfg,on:false,d:null,sel:null,capa:L.layerGroup(),render:L.canvas({pane:'pane_datos',padding:.4})};
  const d=el('details','dtipo'), s=el('summary',null,`${ICONO[id]||'📍'} ${cfg.titulo} (${fmt(cfg.n)})`);
  const body=el('div','dbody'); d.append(s,body); t.ui=d;
  const lb=el('label','dchk'), chk=el('input','don'); chk.type='checkbox'; t.chk=chk;
  lb.append(chk,'Mostrar en el mapa'); body.appendChild(lb);
  const fl=el('div','dfil'); t.fl=fl; body.appendChild(fl);
  crearFiltros(t,fl);
  t.cuenta=el('div','dcount'); t.leg=el('div','dleg'); fl.append(t.cuenta,t.leg);
  const bt=el('div','dbtns'), vl=el('label'), vc=el('input','dvista'); vc.type='checkbox'; t.vista=vc; vl.append(vc,'Solo lo visible');
  const b1=el('button',null,'📋 Ver tabla'), b2=el('button',null,'⬇ CSV'), b3=el('button',null,'Limpiar filtros');
  b1.onclick=()=>abrirTabla(t); b2.onclick=()=>exportarCSV(t); b3.onclick=()=>limpiar(t);
  vc.onchange=()=>aplicar(t); bt.append(b1,b2,b3,vl); fl.appendChild(bt);
  chk.onchange=()=>activar(t,chk.checked);
  return d;
}
map.on('moveend',()=>{ for(const t of Object.values(T)) if(t.on&&t.vista.checked) programar(t); });

fetch('capas.json').then(r=>r.json()).then(cs=>cs.forEach(c=>{ if(c.informe&&c.pdf&&!PDF_GB[c.informe]) PDF_GB[c.informe]=c.pdf; })).catch(()=>{});
fetch('datos/index.json'+DATA_V).then(r=>{ if(!r.ok) throw new Error(r.status); return r.json(); }).then(idx=>{
  INDEX=idx;
  const ids=Object.keys(idx.tipos); if(!ids.length) return;
  const total=ids.reduce((a,k)=>a+idx.tipos[k].n,0);
  const d=el('details'), s=el('summary',null,`📍 Datos de las GDB (${fmt(total)} puntos)`); d.appendChild(s);
  const nota=el('div','vacio','Dataciones, fósiles, yacimientos y mediciones estructurales de las cartas con GDB. Marca un tipo y filtra, p. ej. Método U-Pb + Época Mioceno.');
  d.appendChild(nota);
  ids.forEach(id=>d.appendChild(crearTipo(id,idx.tipos[id])));
  sec.appendChild(d);
}).catch(e=>console.warn('Sin datos puntuales:',e));
})();
