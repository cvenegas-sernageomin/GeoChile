/* Datos puntuales de las GDB (geocronología, fósiles, yacimientos, estructuras) con filtros.
   Lee datos/index.json (generado por tools/exportar_gdb_a_datos.py) y construye la interfaz sola:
   cada tipo trae sus filtros (multi / rango / texto). Usa globals del visor: map, L, PANE_GIRA, panel, togglePanel. */
(function(){
'use strict';
const DATA_V='?v=20261016a';   // subir al regenerar datos/ (el service worker los guarda con caché primero)
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
.ddbtn{width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;text-align:left;font-size:14px;min-height:38px;padding:6px 10px;border:1px solid #cbd5e1;background:#fff;border-radius:8px;cursor:pointer;color:#1e293b}
.ddbtn b{font-weight:600}
.ddbtn.act{border-color:#1a5276;background:#eaf2f8}
.ddbtn .fl{font-size:11px;color:#1a5276}
.ddpanel{display:none;border:1px solid #cbd5e1;border-radius:8px;margin-top:4px;background:#fff;overflow:hidden}
.ddpanel.on{display:block}
.ddtop{display:flex;flex-wrap:wrap;gap:6px;padding:6px;background:#f1f5f9;border-bottom:1px solid #e2e8f0}
.ddtop input{flex:1 1 130px;min-width:0;font-size:14px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:8px}
.ddtop button{font-size:12.5px;border:1px solid #cbd5e1;background:#fff;border-radius:8px;padding:6px 9px;cursor:pointer;min-height:34px}
.ddlist{max-height:240px;overflow-y:auto;-webkit-overflow-scrolling:touch}
.ddopt{display:flex;align-items:center;gap:8px;padding:7px 10px;font-size:13.5px;cursor:pointer;min-height:36px;border-bottom:1px solid #f1f5f9}
.ddopt:hover{background:#f1f5f9}
.ddopt input{width:18px;height:18px;margin:0;accent-color:#1a5276;flex:none}
.ddopt span{flex:1}
.ddopt small{color:#64748b}
.ddgrp{display:flex;align-items:center;gap:8px;padding:5px 10px;font-size:12px;font-weight:700;color:#1a5276;background:#eaf2f8;position:sticky;top:0;cursor:pointer}
.ddgrp input{width:16px;height:16px;margin:0;accent-color:#1a5276}
.ddrare{padding:5px 10px;font-size:11.5px;font-weight:700;color:#64748b;background:#f8fafc;text-transform:uppercase;letter-spacing:.04em}
.dlimpiar{margin-left:auto;font-size:13px;font-weight:600;color:#9b1c1c;border:1px solid #e5b4b4;background:#fff5f5;border-radius:8px;padding:6px 11px;cursor:pointer;min-height:34px}
.dtop{display:flex;align-items:center;gap:8px;margin-top:8px}
.detq{position:relative;width:0;height:0}
.detq .eb{position:absolute;left:-1px;bottom:12px;display:flex;align-items:center;gap:4px;background:#fff;color:#111;border:1px solid #111;padding:0 5px 0 4px;white-space:nowrap;
  box-shadow:0 1px 5px rgba(0,0,0,.45);font:600 12.5px/1 Arial,Helvetica,sans-serif;cursor:pointer}
.detq .eb svg{width:13px;height:13px;flex:none}
.detq .eb span{padding:4px 0 3px}
.detq .ep{position:absolute;left:-.5px;bottom:0;width:1px;height:12px;background:#111;box-shadow:0 0 0 1px rgba(255,255,255,.55)}
.detq .epu{position:absolute;left:-3.5px;bottom:-3.5px;width:7px;height:7px;background:#111;border:1px solid #fff}
.dhint{font-size:11.5px;color:#64748b;margin-top:4px}
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
      const ok=new Set(); c.d.forEach((n,j)=>{ if(f.sep?n.split(f.sep).some(p=>e.has(p)):e.has(n)) ok.add(j); });
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
  etiquetar(t);
  // leyenda de colores con lo que hay en la selección
  const cnt={}, c=t.col[t.cfg.color_por];
  if(c) for(const i of t.sel){ const j=c.v[i]; const n=j<0?'(sin dato)':c.d[j]; cnt[n]=(cnt[n]||0)+1; }
  t.leg.replaceChildren(...Object.entries(cnt).sort((a,b)=>b[1]-a[1]).slice(0,12).map(([n,k])=>{
    const s=el('span'); const i=el('i'); i.style.background=t.colores[n]||'#999'; s.append(i,`${n} (${fmt(k)})`); return s; }));
}
/* ---- etiquetas de edad (geocronología), estilo carta/GeoLente: caja blanca, símbolo del método, edad ---- */
const SIMB={
  'U-Pb':'<path d="M7 1.6 13 12.4H1Z"/>',
  'U-Pb det':'<path d="M7 1.6 13 12.4H1Z"/><circle cx="7" cy="8.6" r="1.4" fill="currentColor"/>',
  'Ar-Ar':'<path d="M7 1 13 7 7 13 1 7Z"/><circle cx="7" cy="7" r="1.5" fill="currentColor"/>',
  'K-Ar':'<rect x="1.5" y="1.5" width="11" height="11"/>',
  '14C':'<path d="M1 1.6H13L7 12.4Z M7 1.6V12.4"/>',
  otro:'<circle cx="7" cy="7" r="4.6"/>'
};
const ZOOM_ETQ_MIN=9;
const topeEtq=z=>z>=13?110:z>=12?80:z>=11?55:z>=10?35:20;
function txtEdad(t,i){
  let e=valor(t,'edad_txt',i);
  if(e) e=e.replace(/\s*\(=.*$/,'').replace(/\s*±\s*/g,'±').replace(/(\d)\.(\d)/g,'$1,$2').replace(/\ba AP$/,'años AP').replace(/\s+/g,' ').trim();
  else { const m=valor(t,'edad_ma',i); e=m==null?'?':(m<1?m.toFixed(3):m.toFixed(1)).replace('.',',')+' Ma'; }
  return e;
}
function simbolo(t,i){
  const m=valor(t,'metodo',i), mat=valor(t,'material',i)||'';
  const k=m==='U-Pb'&&/detr/i.test(mat)?'U-Pb det':(SIMB[m]?m:'otro');
  return `<svg viewBox="0 0 14 14" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.3">${SIMB[k]}</g></svg>`;
}
const PRIO={'U-Pb':0,'Ar-Ar':1,'K-Ar':2,'14C':3};
function etiquetar(t){
  if(t.id!=='geocronologia') return;
  if(!t.etq){ t.etq=L.layerGroup(); }
  t.etq.clearLayers();
  const z=map.getZoom();
  if(!t.on||!t.sel||z<ZOOM_ETQ_MIN){ if(map.hasLayer(t.etq)) t.etq.remove(); return; }
  if(!map.hasLayer(t.etq)) t.etq.addTo(map);
  const b=map.getBounds().pad(.05), cand=[];
  for(const i of t.sel){ if(b.contains([lat(t,i),lon(t,i)])) cand.push(i); }
  const m=t.col.metodo, er=t.col.error_ma, pr=i=>{ const j=m?m.v[i]:-1; return j<0?9:(PRIO[m.d[j]]??5); };
  cand.sort((a,c)=>pr(a)-pr(c) || ((er?er.v[a]:0)??9e9)-((er?er.v[c]:0)??9e9));
  const tope=topeEtq(z), puestos=[];
  for(const i of cand){
    if(puestos.length>=tope) break;
    const txt=txtEdad(t,i), p=map.latLngToContainerPoint([lat(t,i),lon(t,i)]);
    const w=txt.length*7.4+30, h=20, x0=p.x-1, y0=p.y-12-h;
    if(puestos.some(q=>x0<q[2]&&x0+w>q[0]&&y0<q[3]&&y0+h>q[1])) continue;
    puestos.push([x0,y0,x0+w,y0+h]);
    const ic=L.divIcon({className:'detq',html:`<div class="ep"></div><div class="epu"></div><div class="eb">${simbolo(t,i)}<span></span></div>`,iconSize:[0,0],iconAnchor:[0,0]});
    const mk=L.marker([lat(t,i),lon(t,i)],{icon:ic,pane:'pane_datos',keyboard:false,riseOnHover:true});
    mk.on('add',()=>{ const sp=mk.getElement().querySelector('.eb span'); if(sp) sp.textContent=txt; });
    mk.on('click',e=>{ L.DomEvent.stopPropagation(e); abrirPopup(t,i,e.latlng); });
    t.etq.addLayer(mk);
  }
}
let debEtq=null;
map.on('moveend zoomend',()=>{ clearTimeout(debEtq); debEtq=setTimeout(()=>{ const t=T.geocronologia; if(t&&t.on&&t.sel) etiquetar(t); },140); });
function abrirPopup(t,i,ll){
  const div=el('div','dpop'); div.appendChild(el('h4',null,t.cfg.titulo));
  const tb=el('table');
  for(const [k,et] of t.cfg.popup){
    let v=valor(t,k,i); if(v==null||v==='') continue;
    if(k==='region') v=String(v).replace(/\|/g,' · ');
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
function celda(v){ return v==null?'':String(v).replace(/\|/g,' · '); }
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
const ANTIGUOS=['Rb-Sr','Sm-Nd','Re-Os','Pb/Alpha','Trazas de fisión','Sin método','Otro método (sin especificar)'];
function crearMulti(t,f,g){
  const sel=t.fil[f.campo]=new Set(), total=f.valores.reduce((a,v)=>a+v[1],0);
  // opciones: las poco usadas (o métodos antiguos) van al final bajo «Menos usados»; las épocas van agrupadas por era · periodo
  let principales=f.valores, raras=[];
  if(f.campo!=='epoca' && f.valores.length>8){
    const raro=([v,n])=>(f.campo==='metodo'&&ANTIGUOS.includes(v)) || n<Math.max(3,total*.005);
    principales=f.valores.filter(x=>!raro(x)); raras=f.valores.filter(raro);
    if(f.campo==='metodo') raras.sort((a,b)=>ANTIGUOS.includes(a[0])-ANTIGUOS.includes(b[0]) || b[1]-a[1]);
  }
  const btn=el('button','ddbtn'); btn.type='button';
  const panel=el('div','ddpanel');
  const top=el('div','ddtop'), q=el('input'); q.type='search'; q.placeholder='Buscar…'; q.setAttribute('aria-label','Buscar en '+f.etiqueta);
  const bVis=el('button',null,'Marcar visibles'), bNin=el('button',null,'Quitar selección');
  bVis.type=bNin.type='button';
  if(f.valores.length>8) top.appendChild(q);
  top.append(bVis,bNin); panel.appendChild(top);
  const lista=el('div','ddlist'); panel.appendChild(lista);
  const filas=[];   // {row, cb, v, key, grp}
  const cabeceras=[];
  let resumen=()=>{};
  const fila=(v,n,grp)=>{
    const lb=el('label','ddopt'), cb=el('input'); cb.type='checkbox';
    lb.append(cb,el('span',null,v),el('small',null,fmt(n)));
    cb.onchange=()=>{ cb.checked?sel.add(v):sel.delete(v); resumen(); programar(t); };
    lista.appendChild(lb); filas.push({row:lb,cb,v,key:norm(v+' '+(grp||'')),grp});
  };
  if(f.grupos){
    let ult=null;
    for(const [v,n] of principales){
      const gr=f.grupos[v]||'';
      if(gr!==ult){
        ult=gr; const h=el('label','ddgrp'), c=el('input'); c.type='checkbox'; h.append(c,gr||'Otros');
        cabeceras.push({row:h,c,gr});
        c.onchange=()=>{ filas.filter(x=>x.grp===gr&&x.row.style.display!=='none').forEach(x=>{ x.cb.checked=c.checked; c.checked?sel.add(x.v):sel.delete(x.v); }); resumen(); programar(t); };
        lista.appendChild(h);
      }
      fila(v,n,gr);
    }
  }else principales.forEach(([v,n])=>fila(v,n));
  let hdrRaras=null;
  if(raras.length){ hdrRaras=el('div','ddrare','Menos usados'); lista.appendChild(hdrRaras); raras.forEach(([v,n])=>fila(v,n)); }
  resumen=()=>{
    const n=sel.size; btn.classList.toggle('act',n>0);
    btn.replaceChildren(el('b',null,f.etiqueta),el('span','fl',(n?`${n} de ${f.valores.length}`:'todos')+(panel.classList.contains('on')?' ▴':' ▾')));
    cabeceras.forEach(h=>{ const m=filas.filter(x=>x.grp===h.gr); h.c.checked=m.length>0&&m.every(x=>x.cb.checked); });
  };
  const filtrar=()=>{
    const k=norm(q.value).split(/\s+/).filter(Boolean);
    filas.forEach(x=>{ x.row.style.display=k.every(w=>x.key.includes(w))?'':'none'; });
    cabeceras.forEach(h=>{ h.row.style.display=filas.some(x=>x.grp===h.gr&&x.row.style.display!=='none')?'':'none'; });
    if(hdrRaras) hdrRaras.style.display=filas.slice(principales.length).some(x=>x.row.style.display!=='none')?'':'none';
  };
  q.oninput=filtrar;
  bVis.onclick=()=>{ filas.forEach(x=>{ if(x.row.style.display!=='none'){ x.cb.checked=true; sel.add(x.v); } }); resumen(); programar(t); };
  bNin.onclick=()=>{ filas.forEach(x=>{ x.cb.checked=false; }); sel.clear(); resumen(); programar(t); };
  btn.onclick=()=>{
    const abrir=!panel.classList.contains('on');
    t.ui.querySelectorAll('.ddpanel.on').forEach(p=>p.classList.remove('on'));
    panel.classList.toggle('on',abrir); t.ui.querySelectorAll('.ddbtn').forEach(b=>b._r&&b._r());
    if(abrir&&f.valores.length>8&&!matchMedia('(pointer:coarse)').matches) q.focus();
  };
  btn._r=resumen; t.resets.push(()=>{ filas.forEach(x=>{x.cb.checked=false;}); q.value=''; filtrar(); resumen(); });
  resumen(); g.append(btn,panel);
}
function crearFiltros(t,cont){
  t.fil={}; t.resets=[];
  for(const f of t.cfg.filtros){
    const g=el('div','dgrp');
    if(f.control==='multi'){
      crearMulti(t,f,g);
    }else if(f.control==='rango'){
      g.appendChild(el('b',null,f.etiqueta));
      const e=t.fil[f.campo]={min:null,max:null}, w=el('div','drango');
      const a=el('input'), b=el('input'); a.type=b.type='number'; a.step=b.step='any';
      a.placeholder='mín '+f.min; b.placeholder='máx '+f.max; a.setAttribute('aria-label',f.etiqueta+' mínimo'); b.setAttribute('aria-label',f.etiqueta+' máximo');
      const lee=()=>{ e.min=a.value===''?null:+a.value; e.max=b.value===''?null:+b.value; programar(t); };
      a.oninput=b.oninput=lee; w.append(a,'–',b); g.appendChild(w);
    }else{
      g.appendChild(el('b',null,f.etiqueta));
      const e=t.fil[f.campo]={q:''}, i=el('input','dtxt'); i.type='search'; i.placeholder=f.etiqueta+'…';
      i.oninput=()=>{ e.q=i.value.trim(); programar(t); }; g.appendChild(i);
    }
    cont.appendChild(g);
  }
}
function limpiar(t){
  t.resets.forEach(f=>f());
  t.ui.querySelectorAll('.drango input,.dtxt').forEach(i=>{i.value='';});
  for(const f of t.cfg.filtros){ const e=t.fil[f.campo];
    if(f.control==='multi') e.clear(); else if(f.control==='rango'){e.min=e.max=null;} else e.q=''; }
  aplicar(t);
}
document.addEventListener('click',ev=>{   // tocar fuera cierra los desplegables
  document.querySelectorAll('#datos .ddpanel.on').forEach(p=>{
    if(!p.parentElement.contains(ev.target)){ p.classList.remove('on'); const b=p.previousElementSibling; if(b&&b._r) b._r(); }
  });
});
async function activar(t,on){
  t.on=on; t.fl.classList.toggle('on',on);
  if(!on){ t.capa.remove(); if(t.etq) t.etq.remove(); t.sel=null; pintarResumen(); return; }
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
  const tp=el('div','dtop'), bl=el('button','dlimpiar','✕ Limpiar todo'); bl.type='button'; bl.onclick=()=>limpiar(t);
  t.cuenta=el('div','dcount'); t.cuenta.style.margin='0'; tp.append(t.cuenta,bl); fl.appendChild(tp);
  crearFiltros(t,fl);
  t.leg=el('div','dleg'); fl.appendChild(t.leg);
  if(id==='geocronologia') fl.appendChild(el('div','dhint','Las etiquetas de edad aparecen al acercar el mapa (desde zoom 9); cuanto más cerca, más etiquetas.'));
  const bt=el('div','dbtns'), vl=el('label'), vc=el('input','dvista'); vc.type='checkbox'; t.vista=vc; vl.append(vc,'Solo lo visible');
  const b1=el('button',null,'📋 Ver tabla'), b2=el('button',null,'⬇ CSV');
  b1.onclick=()=>abrirTabla(t); b2.onclick=()=>exportarCSV(t);
  vc.onchange=()=>aplicar(t); bt.append(b1,b2,vl); fl.appendChild(bt);
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
