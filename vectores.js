/* Unidades geológicas (polígonos) y fallas de las GDB, con filtros por edad, litología y ambiente.
   Datos: repo geochile-vectores (un JSON por carta, se descargan solo las cartas que se ven y desde zoom 9).
   Reutiliza de datos.js (window.GCDATOS) los filtros desplegables. La litología es INFERIDA del texto de la unidad:
   la GDB no trae un campo de litología en las unidades. */
(function(){
'use strict';
const G=window.GCDATOS;
if(!G||typeof map==='undefined') return;
const {el,fmt,norm,crearMulti,programar}=G;
const sec=document.getElementById('datos');
const BASE='https://cvenegas-sernageomin.github.io/geochile-vectores/';
const VEC_V='?v=20261016';
const ZOOM_MIN=9, MAX_CARTAS=14;
const ENCABEZADO={Holoceno:'Cenozoico · Cuaternario',Pleistoceno:'Cenozoico · Cuaternario',Plioceno:'Cenozoico · Neógeno',Mioceno:'Cenozoico · Neógeno',
  Oligoceno:'Cenozoico · Paleógeno',Eoceno:'Cenozoico · Paleógeno',Paleoceno:'Cenozoico · Paleógeno','Cretácico Superior':'Mesozoico · Cretácico',
  'Cretácico Inferior':'Mesozoico · Cretácico','Jurásico Superior':'Mesozoico · Jurásico','Jurásico Medio':'Mesozoico · Jurásico','Jurásico Inferior':'Mesozoico · Jurásico',
  'Triásico Superior':'Mesozoico · Triásico','Triásico Medio':'Mesozoico · Triásico','Triásico Inferior':'Mesozoico · Triásico','Pérmico':'Paleozoico · Pérmico',
  'Carbonífero':'Paleozoico · Carbonífero','Devónico':'Paleozoico · Devónico','Silúrico':'Paleozoico · Silúrico','Ordovícico':'Paleozoico · Ordovícico',
  'Cámbrico':'Paleozoico · Cámbrico','Precámbrico':'Precámbrico'};
/* colores: periodos (ICS), litología y ambiente */
const PERIODOS=[[2.58,'Cuaternario','#F9F97F'],[23.03,'Neógeno','#FFE619'],[66,'Paleógeno','#FD9A52'],[145,'Cretácico','#7FC64E'],[201.4,'Jurásico','#34B2C9'],
  [251.9,'Triásico','#812B92'],[298.9,'Pérmico','#F04028'],[358.9,'Carbonífero','#67A599'],[419.2,'Devónico','#CB8C37'],[443.8,'Silúrico','#B3E1B6'],
  [485.4,'Ordovícico','#009270'],[538.8,'Cámbrico','#7FA056'],[1e9,'Precámbrico','#F74370']];
const SIN='#b8bec6';
const COL_LIT={'Plutónicas':'#e6194b','Subvolcánicas':'#f58231','Volcánicas':'#9a6324','Sedimentarias clásticas':'#d9b300','Carbonáticas':'#4363d8',
  'Metamórficas':'#3cb44b','Depósitos no consolidados':'#e8dfa0','Sin litología reconocida':SIN};
const COL_AMB={'Sedimentario':'#d9b300','Volcánico':'#9a6324','Plutónico / intrusivo':'#e6194b','Volcánico-sedimentario':'#c98a4b','Subvolcánico (hipabisal)':'#f58231',
  'Metamórfico':'#3cb44b','Tectónico':'#7f7f7f','Antrópico':'#7f7f7f','Sin dato':SIN};
const COL_FALLA=[[/inversa|cabalgam/i,'#d62828'],[/normal/i,'#1d4ed8'],[/rumbo|transcurr|sinestral|dextral/i,'#15803d'],[/fotolinea|lineam/i,'#94a3b8'],[/.*/,'#334155']];
const periodoDe=ma=>{ for(const [lim,n,c] of PERIODOS) if(ma<lim) return [n,c]; return ['Precámbrico','#F74370']; };

const css=document.createElement('style');
css.textContent=`
.vsel{width:100%;font-size:14px;padding:7px 8px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;min-height:38px}
.vmsg{font-size:12.5px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:6px 9px;margin:6px 0;display:none}
.vmsg.on{display:block}
.vnota{font-size:11.5px;color:#64748b;margin-top:6px;line-height:1.4}
`;
document.head.appendChild(css);

let IDX=null; const CARTAS=new Map();   // id -> datos de la carta ya descargada
map.createPane('pane_vec',PANE_GIRA).style.zIndex=430;
map.createPane('pane_vecf',PANE_GIRA).style.zIndex=435;
const rU=L.canvas({pane:'pane_vec',padding:.3}), rF=L.canvas({pane:'pane_vecf',padding:.3});
const capaU=L.layerGroup(), capaF=L.layerGroup();
const U={id:'vec_u',on:false,fil:{},resets:[]}, F={id:'vec_f',on:false,fil:{},resets:[]};
const extra={colorear:'edad',rango:{min:null,max:null},q:''};

/* ---------- carga por vista ---------- */
const cartasEnVista=()=>{
  const b=map.getBounds().pad(.05), c=map.getCenter();
  return IDX.cartas.filter(k=>{ const [w,s,e,n]=k.bounds; return !(e<b.getWest()||w>b.getEast()||n<b.getSouth()||s>b.getNorth()); })
    .sort((a,k)=>dist(a,c)-dist(k,c));
};
const dist=(k,c)=>{ const [w,s,e,n]=k.bounds; return Math.hypot((w+e)/2-c.lng,(s+n)/2-c.lat); };
async function traer(k){
  if(CARTAS.has(k.id)) return CARTAS.get(k.id);
  const p=fetch(BASE+'cartas/'+k.id+'.json'+VEC_V).then(r=>{ if(!r.ok) throw new Error(r.status); return r.json(); }).then(d=>{ prepararCarta(k,d); return d; });
  CARTAS.set(k.id,p);
  p.catch(()=>CARTAS.delete(k.id));
  return p;
}
function prepararCarta(k,d){
  d.k=k;
  d.u.forEach(u=>{ u.nrm=norm((u.n||'')+' '+(u.c||'')+' '+(u.d||'')); });
}

/* ---------- filtros (se evalúan por unidad, no por polígono) ---------- */
function pasaUnidad(u){
  const e=U.fil.epoca; if(e&&e.size){ const ep=u.ep&&u.ep.length?u.ep:['Sin edad']; if(!ep.some(x=>e.has(x))) return false; }
  const r=extra.rango; if(r.min!=null||r.max!=null){
    if(u.mx==null) return false;
    if(r.min!=null&&u.mx<r.min) return false;      // la unidad entera es más joven que el mínimo
    if(r.max!=null&&u.mn>r.max) return false;      // la unidad entera es más vieja que el máximo
  }
  const l=U.fil.litologia; if(l&&l.size&&!l.has(u.lc)) return false;
  const ro=U.fil.roca; if(ro&&ro.size&&!u.lr.some(x=>ro.has(x))) return false;
  const a=U.fil.ambiente; if(a&&a.size&&!a.has(u.a||'Sin dato')) return false;
  if(extra.q){ const t=norm(extra.q).split(/\s+/).filter(Boolean); if(!t.every(w=>u.nrm.includes(w))) return false; }
  return true;
}
function colorUnidad(u){
  const m=extra.colorear;
  if(m==='litologia') return COL_LIT[u.lc]||SIN;
  if(m==='ambiente') return COL_AMB[u.a||'Sin dato']||SIN;
  if(u.mx==null) return SIN;
  return periodoDe((u.mx+u.mn)/2)[1];
}
const colorFalla=t=>{ for(const [re,c] of COL_FALLA) if(re.test(t)) return c; return '#334155'; };

/* ---------- dibujo ---------- */
const GT={0:'Polygon',1:'MultiPolygon',2:'LineString',3:'MultiLineString'};
function dibujar(){
  capaU.clearLayers(); capaF.clearLayers();
  const msg=document.getElementById('vmsg'); let n=0, nf=0, usados=0, leg={};
  const z=map.getZoom(), activo=U.on||F.on;
  const aviso=(t)=>{ msg.textContent=t||''; msg.classList.toggle('on',!!t); };
  if(!activo||!IDX){ aviso(''); actualizarCuenta(0,0,0); return; }
  if(z<ZOOM_MIN){ aviso('Acerca el mapa (zoom 9 o más) para ver unidades y fallas.'); actualizarCuenta(0,0,0); return; }
  const vis=cartasEnVista();
  if(vis.length>MAX_CARTAS) aviso(`Hay ${vis.length} cartas en pantalla; se dibujan las ${MAX_CARTAS} más cercanas al centro. Acerca para ver el resto.`); else aviso('');
  const usar=vis.slice(0,MAX_CARTAS);
  usar.forEach(k=>{
    const d=CARTAS.get(k.id); if(!d||!d.u) return;   // aún es una promesa: se redibuja al llegar
    usados++;
    if(U.on){
      const ok=d.u.map(pasaUnidad), feats=[];
      const cu=d.u.map(colorUnidad);
      for(const [ui,t,c] of d.p) if(ok[ui]){ feats.push({type:'Feature',properties:{u:ui,col:cu[ui]},geometry:{type:GT[t],coordinates:c}}); }
      n+=feats.length;
      if(feats.length){
        const col=feats.map(f=>f.properties.col);
        const gl=L.geoJSON({type:'FeatureCollection',features:feats},{pane:'pane_vec',renderer:rU,smoothFactor:1.2,
          style:f=>({color:'#3b3b3b',weight:.6,fillColor:f.properties.col,fillOpacity:.55}),
          onEachFeature:(f,l)=>{ l.on('click',e=>{ L.DomEvent.stopPropagation(e); popupUnidad(d,f.properties.u,e.latlng); }); }});
        capaU.addLayer(gl);
        feats.forEach((f,j)=>{ const u=d.u[f.properties.u]; const key=nombreLeyenda(u); leg[key]=[col[j],(leg[key]?leg[key][1]:0)+1]; });
      }
    }
    if(F.on){
      const feats=[], fo=F.fil.tipo, ob=F.fil.obs, q=norm(extra.qf||'');
      for(const [ti,nom,obs,man,t,c] of d.f){
        const tipo=d.ft[ti];
        if(fo&&fo.size&&!fo.has(tipo)) continue;
        if(ob&&ob.size&&!ob.has(obs===1?'Observada':obs===2?'Inferida / cubierta':'Sin dato')) continue;
        if(q&&!norm(nom||'').includes(q)&&!norm(tipo).includes(q)) continue;
        feats.push({type:'Feature',properties:{tipo,nom,obs,man,k:k.id},geometry:{type:GT[t],coordinates:c}});
      }
      nf+=feats.length;
      if(feats.length) capaF.addLayer(L.geoJSON({type:'FeatureCollection',features:feats},{pane:'pane_vecf',renderer:rF,smoothFactor:1,
        style:f=>({color:colorFalla(f.properties.tipo),weight:f.properties.obs===1?2:1.4,opacity:.95,dashArray:f.properties.obs===2?'6 5':null}),
        onEachFeature:(f,l)=>{ l.on('click',e=>{ L.DomEvent.stopPropagation(e); popupFalla(f.properties,e.latlng); }); }}));
    }
  });
  actualizarCuenta(n,nf,usados);
  pintarLeyenda(leg);
}
function nombreLeyenda(u){
  const m=extra.colorear;
  if(m==='litologia') return u.lc||'Sin litología reconocida';
  if(m==='ambiente') return u.a||'Sin dato';
  return u.mx==null?'Sin edad':periodoDe((u.mx+u.mn)/2)[0];
}
function pintarLeyenda(leg){
  const box=document.getElementById('vleg'); if(!box) return;
  box.replaceChildren(...Object.entries(leg).sort((a,b)=>b[1][1]-a[1][1]).map(([n,[c,k]])=>{
    const s=el('span'), i=el('i'); i.style.background=c; s.append(i,`${n} (${fmt(k)})`); return s; }));
}
function actualizarCuenta(n,nf,cartas){
  const a=document.getElementById('vcu'), b=document.getElementById('vcf');
  if(a) a.textContent=U.on?`${fmt(n)} polígonos en la vista (${cartas} cartas)`:'';
  if(b) b.textContent=F.on?`${fmt(nf)} fallas en la vista (${cartas} cartas)`:'';
}

/* ---------- popups (DOM, sin innerHTML) ---------- */
function filas(tit,pares,pie){
  const div=el('div','dpop'); div.appendChild(el('h4',null,tit));
  const tb=el('table');
  for(const [k,v] of pares){ if(v==null||v==='') continue; const tr=el('tr'); tr.append(el('td',null,k),el('td',null,String(v))); tb.appendChild(tr); }
  div.appendChild(tb); if(pie) div.appendChild(el('div','fte',pie)); return div;
}
const tituloCarta=d=>{ const k=d.k; return `${k.titulo||''}${k.gb?' · '+k.gb:''}`; };
function popupUnidad(d,ui,ll){
  const u=d.u[ui];
  const edad=u.mx==null?'sin edad':`${(+u.mx).toLocaleString('es-CL')}${u.mn!==u.mx?' – '+(+u.mn).toLocaleString('es-CL'):''} Ma (${u.fe})`;
  const lito=u.lc+(u.lr&&u.lr.length?' — '+u.lr.join(', '):'');
  const p=filas(u.n||u.c||'Unidad geológica',[['Código',u.c],['Definición',u.d],['Ambiente',u.a],['Litología (inferida del texto)',lito],
    ['Periodo',u.pe],['Época',u.em],['Edad',edad]],'Carta: '+tituloCarta(d)+'. Datos de la GDB oficial de SERNAGEOMIN; edad y litología resueltas por GeoChile.');
  L.popup({maxWidth:340}).setLatLng(ll).setContent(p).openOn(map);
}
function popupFalla(p,ll){
  const obs=p.obs===1?'Observada':p.obs===2?'Inferida / cubierta':null;
  const k=IDX.cartas.find(x=>x.id===p.k);
  L.popup({maxWidth:320}).setLatLng(ll).setContent(filas(p.nom||p.tipo,[['Tipo',p.tipo],['Nombre',p.nom],['Trazo',obs],['Manteo',p.man]],k?'Carta: '+k.titulo+(k.gb?' · '+k.gb:''):'')).openOn(map);
}

/* ---------- carga y redibujo ---------- */
let deb=null;
function actualizar(){
  clearTimeout(deb);
  deb=setTimeout(async()=>{
    if(!IDX||!(U.on||F.on)){ dibujar(); return; }
    if(map.getZoom()<ZOOM_MIN){ dibujar(); return; }
    const usar=cartasEnVista().slice(0,MAX_CARTAS);
    const pend=usar.filter(k=>!CARTAS.has(k.id)||!CARTAS.get(k.id).u);
    if(pend.length){
      const msg=document.getElementById('vmsg'); msg.textContent='Cargando '+pend.length+' carta(s)…'; msg.classList.add('on');
      await Promise.all(pend.map(k=>traer(k).catch(()=>null)));
      for(const k of usar){ const v=CARTAS.get(k.id); if(v&&v.then) { try{ CARTAS.set(k.id,await v); }catch(e){} } }
    }
    for(const k of usar){ const v=CARTAS.get(k.id); if(v&&v.then){ try{ CARTAS.set(k.id,await v); }catch(e){} } }
    dibujar();
  },180);
}
map.on('moveend zoomend',actualizar);

/* ---------- interfaz ---------- */
function bloque(id,titulo,icono){
  const d=el('details','dtipo'), s=el('summary',null,`${icono} ${titulo}`); const body=el('div','dbody'); d.append(s,body); return {d,body};
}
function limpiarU(){
  U.resets.forEach(f=>f()); for(const k of Object.keys(U.fil)) U.fil[k].clear();
  extra.rango.min=extra.rango.max=null; extra.q=''; U.ui.querySelectorAll('.drango input,.dtxt').forEach(i=>{i.value='';});
  actualizar();
}
function limpiarF(){
  F.resets.forEach(f=>f()); for(const k of Object.keys(F.fil)) F.fil[k].clear(); extra.qf=''; F.ui.querySelectorAll('.dtxt').forEach(i=>{i.value='';}); actualizar();
}
function construir(idx){
  IDX=idx;
  G.cuenta('lineas',fmt(idx.totales.fallas)+' fallas'); G.cuenta('poligonos',fmt(idx.totales.poligonos)+' polígonos');
  const msg=el('div','vmsg'); msg.id='vmsg'; G.raiz.insertBefore(msg,G.raiz.children[2]);   // aviso de zoom/carga, bajo la explicación

  /* unidades */
  const bu=bloque('u','Unidades geológicas','🧱'); U.ui=bu.d;
  const lb=el('label','dchk'), chk=el('input','don'); chk.type='checkbox'; lb.append(chk,'Mostrar en el mapa'); bu.body.appendChild(lb);
  const fl=el('div','dfil'); bu.body.appendChild(fl);
  const tp=el('div','dtop'), cu=el('div','dcount'); cu.id='vcu'; cu.style.margin='0'; const bl=el('button','dlimpiar','✕ Limpiar todo'); bl.type='button'; bl.onclick=limpiarU;
  tp.append(cu,bl); fl.appendChild(tp);
  const gc=el('div','dgrp'); gc.appendChild(el('b',null,'Colorear por'));
  const sel=el('select','vsel'); [['edad','Edad (periodo)'],['litologia','Litología'],['ambiente','Ambiente']].forEach(([v,t])=>{ const o=el('option',null,t); o.value=v; sel.appendChild(o); });
  sel.onchange=()=>{ extra.colorear=sel.value; dibujar(); }; gc.appendChild(sel); fl.appendChild(gc);
  const F0=idx.filtros;
  const mk=(campo,etq,valores,extraF)=>{ const g=el('div','dgrp'); crearMulti(U,Object.assign({campo,etiqueta:etq,valores},extraF||{}),g); fl.appendChild(g); };
  U.fil={};
  mk('epoca','Época',F0.epoca,{grupos:ENCABEZADO});
  const gr=el('div','dgrp'); gr.appendChild(el('b',null,'Edad (Ma)')); const w=el('div','drango'), a=el('input'), b=el('input');
  a.type=b.type='number'; a.step=b.step='any'; a.placeholder='mín 0'; b.placeholder='máx 600'; a.setAttribute('aria-label','Edad mínima en Ma'); b.setAttribute('aria-label','Edad máxima en Ma');
  a.oninput=b.oninput=()=>{ extra.rango.min=a.value===''?null:+a.value; extra.rango.max=b.value===''?null:+b.value; actualizar(); };
  w.append(a,'–',b); gr.appendChild(w); fl.appendChild(gr);
  mk('litologia','Litología (inferida del texto)',F0.litologia);
  mk('roca','Roca o material (inferido)',F0.roca);
  mk('ambiente','Ambiente',F0.ambiente);
  const gq=el('div','dgrp'); gq.appendChild(el('b',null,'Buscar en nombre, código o definición')); const q=el('input','dtxt'); q.type='search'; q.placeholder='p. ej. granodiorita, Formación…';
  q.oninput=()=>{ extra.q=q.value.trim(); actualizar(); }; gq.appendChild(q); fl.appendChild(gq);
  fl.appendChild(Object.assign(el('div','dleg'),{id:'vleg'}));
  fl.appendChild(el('div','vnota','La litología se infiere del nombre y la definición de cada unidad (la GDB no la trae como campo). «Sin edad» = la unidad no declara época, periodo ni edad numérica.'));
  chk.onchange=()=>{ U.on=chk.checked; fl.classList.toggle('on',U.on); if(U.on) capaU.addTo(map); else capaU.remove(); actualizar(); };

  /* fallas */
  const bf=bloque('f','Fallas','⚡'); F.ui=bf.d;
  const lf=el('label','dchk'), cf=el('input','don'); cf.type='checkbox'; lf.append(cf,'Mostrar en el mapa'); bf.body.appendChild(lf);
  const ff=el('div','dfil'); bf.body.appendChild(ff);
  const tf=el('div','dtop'), cn=el('div','dcount'); cn.id='vcf'; cn.style.margin='0'; const blf=el('button','dlimpiar','✕ Limpiar todo'); blf.type='button'; blf.onclick=limpiarF;
  tf.append(cn,blf); ff.appendChild(tf);
  F.fil={};
  const g1=el('div','dgrp'); crearMulti(F,{campo:'tipo',etiqueta:'Tipo de falla',valores:F0.falla},g1); ff.appendChild(g1);
  const g2=el('div','dgrp'); crearMulti(F,{campo:'obs',etiqueta:'Trazo',valores:[['Observada',0],['Inferida / cubierta',0],['Sin dato',0]]},g2); ff.appendChild(g2);
  const gn=el('div','dgrp'); gn.appendChild(el('b',null,'Buscar por nombre o tipo')); const qf=el('input','dtxt'); qf.type='search'; qf.placeholder='p. ej. Atacama…';
  qf.oninput=()=>{ extra.qf=qf.value.trim(); actualizar(); }; gn.appendChild(qf); ff.appendChild(gn);
  ff.appendChild(el('div','vnota','Rojo: inversas · azul: normales · verde: de rumbo · gris: indeterminadas y fotolineamientos. Línea punteada: trazo inferido o cubierto.'));
  cf.onchange=()=>{ F.on=cf.checked; ff.classList.toggle('on',F.on); if(F.on) capaF.addTo(map); else capaF.remove(); actualizar(); };

  G.grupo('poligonos').appendChild(bu.d); G.grupo('lineas').appendChild(bf.d);
  [['poligonos',bu.d],['lineas',bf.d]].forEach(([g,d])=>{ d.open=false; });
  // programar() de datos.js llama a t.aplicar: aquí es redibujar
  U.aplicar=actualizar; F.aplicar=actualizar; U.id='vec_u'; F.id='vec_f';
}
fetch(BASE+'index.json'+VEC_V).then(r=>{ if(!r.ok) throw new Error(r.status); return r.json(); }).then(construir)
  .catch(e=>console.warn('Sin vectores (geochile-vectores):',e));
})();
