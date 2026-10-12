// Declinación magnética WMM2025 (copiado de Geonotas index.html, v141). declinacionMagnetica(lat,lon) → grados, + = este.
const WMM_EPOCA=2025.0;
const WMM_COEF=[-29351.8,0.0,12.0,0.0,-1410.8,4545.4,9.7,-21.5,-2556.6,0.0,-11.6,0.0,2951.1,-3133.6,-5.2,-27.7,1649.3,-815.1,-8.0,-12.1,1361.0,0.0,-1.3,0.0,-2404.1,-56.6,-4.2,4.0,1243.8,237.5,0.4,-0.3,453.6,-549.5,-15.6,-4.1,895.0,0.0,-1.6,0.0,799.5,278.6,-2.4,-1.1,55.7,-133.9,-6.0,4.1,-281.1,212.0,5.6,1.6,12.1,-375.6,-7.0,-4.4,-233.2,0.0,0.6,0.0,368.9,45.4,1.4,-0.5,187.2,220.2,0.0,2.2,-138.7,-122.9,0.6,0.4,-142.0,43.0,2.2,1.7,20.9,106.1,0.9,1.9,64.4,0.0,-0.2,0.0,63.8,-18.4,-0.4,0.3,76.9,16.8,0.9,-1.6,-115.7,48.8,1.2,-0.4,-40.9,-59.8,-0.9,0.9,14.9,10.9,0.3,0.7,-60.7,72.7,0.9,0.9,79.5,0.0,-0.0,0.0,-77.0,-48.9,-0.1,0.6,-8.8,-14.4,-0.1,0.5,59.3,-1.0,0.5,-0.8,15.8,23.4,-0.1,0.0,2.5,-7.4,-0.8,-1.0,-11.1,-25.1,-0.8,0.6,14.2,-2.3,0.8,-0.2,23.2,0.0,-0.1,0.0,10.8,7.1,0.2,-0.2,-17.5,-12.6,0.0,0.5,2.0,11.4,0.5,-0.4,-21.7,-9.7,-0.1,0.4,16.9,12.7,0.3,-0.5,15.0,0.7,0.2,-0.6,-16.8,-5.2,-0.0,0.3,0.9,3.9,0.2,0.2,4.6,0.0,-0.0,0.0,7.8,-24.8,-0.1,-0.3,3.0,12.2,0.1,0.3,-0.2,8.3,0.3,-0.3,-2.5,-3.3,-0.3,0.3,-13.1,-5.2,0.0,0.2,2.4,7.2,0.3,-0.1,8.6,-0.6,-0.1,-0.2,-8.7,0.8,0.1,0.4,-12.9,10.0,-0.1,0.1,-1.3,0.0,0.1,0.0,-6.4,3.3,0.0,0.0,0.2,0.0,0.1,-0.0,2.0,2.4,0.1,-0.2,-1.0,5.3,-0.0,0.1,-0.6,-9.1,-0.3,-0.1,-0.9,0.4,0.0,0.1,1.5,-4.2,-0.1,0.0,0.9,-3.8,-0.1,-0.1,-2.7,0.9,-0.0,0.2,-3.9,-9.1,-0.0,-0.0,2.9,0.0,0.0,0.0,-1.5,0.0,-0.0,-0.0,-2.5,2.9,0.0,0.1,2.4,-0.6,0.0,-0.0,-0.6,0.2,0.0,0.1,-0.1,0.5,-0.1,-0.0,-0.6,-0.3,0.0,-0.0,-0.1,-1.2,-0.0,0.1,1.1,-1.7,-0.1,-0.0,-1.0,-2.9,-0.1,0.0,-0.2,-1.8,-0.1,0.0,2.6,-2.3,-0.1,0.0,-2.0,0.0,0.0,0.0,-0.2,-1.3,0.0,-0.0,0.3,0.7,-0.0,0.0,1.2,1.0,-0.0,-0.1,-1.3,-1.4,-0.0,0.1,0.6,-0.0,-0.0,-0.0,0.6,0.6,0.1,-0.0,0.5,-0.1,-0.0,-0.0,-0.1,0.8,0.0,0.0,-0.4,0.1,0.0,-0.0,-0.2,-1.0,-0.1,-0.0,-1.3,0.1,-0.0,0.0,-0.7,0.2,-0.1,-0.1];
let _wmmTabla=null;
function wmmTabla(){
  if(_wmmTabla) return _wmmTabla;
  const N=12, g=[],h=[],gd=[],hd=[];
  for(let n=0;n<=N;n++){g.push(new Float64Array(N+1));h.push(new Float64Array(N+1));gd.push(new Float64Array(N+1));hd.push(new Float64Array(N+1));}
  let k=0;
  for(let n=1;n<=N;n++) for(let m=0;m<=n;m++){ g[n][m]=WMM_COEF[k++]; h[n][m]=WMM_COEF[k++]; gd[n][m]=WMM_COEF[k++]; hd[n][m]=WMM_COEF[k++]; }
  return _wmmTabla={N,g,h,gd,hd};
}
function anioDecimal(fecha){
  const y=fecha.getUTCFullYear(), t0=Date.UTC(y,0,1), t1=Date.UTC(y+1,0,1);
  return y+(fecha.getTime()-t0)/(t1-t0);
}
// Declinación en grados (positiva = norte magnético al ESTE del geográfico), a cota altKm sobre el
// elipsoide. Algoritmo del informe técnico WMM: geodésica → geocéntrica, Legendre de Schmidt
// semi-normalizadas, campo en el marco geocéntrico y rotación al marco geodésico (X norte, Y este).
function declinacionMagnetica(lat,lon,altKm=0,fecha=new Date()){
  const {N,g,h,gd,hd}=wmmTabla();
  const dt=anioDecimal(fecha)-WMM_EPOCA;
  const a=6378.137, f=1/298.257223563, e2=f*(2-f), re=6371.2;
  const phi=lat*Math.PI/180, lam=lon*Math.PI/180;
  const Rc=a/Math.sqrt(1-e2*Math.sin(phi)**2);
  const p=(Rc+altKm)*Math.cos(phi), z=(Rc*(1-e2)+altKm)*Math.sin(phi);
  const r=Math.hypot(p,z), phiP=Math.asin(z/r);
  // Legendre de Schmidt semi-normalizadas P[n][m](sin φ') y sus derivadas respecto de φ'
  const x=Math.sin(phiP), cx=Math.cos(phiP);
  const P=[],dP=[];
  for(let n=0;n<=N;n++){P.push(new Float64Array(N+1));dP.push(new Float64Array(N+1));}
  P[0][0]=1; dP[0][0]=0;
  for(let n=1;n<=N;n++) for(let m=0;m<=n;m++){
    if(n===m){
      const k=n===1?1:Math.sqrt((2*n-1)/(2*n));
      P[n][m]=k*cx*P[n-1][m-1]; dP[n][m]=k*(cx*dP[n-1][m-1]-x*P[n-1][m-1]);
    } else {
      const k1=(2*n-1)/Math.sqrt(n*n-m*m), k2=Math.sqrt(((n-1)*(n-1)-m*m)/(n*n-m*m));
      P[n][m]=k1*x*P[n-1][m]-(n>1&&m<=n-2?k2*P[n-2][m]:0);
      dP[n][m]=k1*(x*dP[n-1][m]+cx*P[n-1][m])-(n>1&&m<=n-2?k2*dP[n-2][m]:0);
    }
  }
  let Xp=0,Yp=0,Zp=0;
  for(let n=1;n<=N;n++){
    const fr=Math.pow(re/r,n+2);
    for(let m=0;m<=n;m++){
      const gg=g[n][m]+dt*gd[n][m], hh=h[n][m]+dt*hd[n][m];
      const cm=Math.cos(m*lam), sm=Math.sin(m*lam);
      Xp+=-fr*(gg*cm+hh*sm)*dP[n][m];
      Yp+=fr*m*(gg*sm-hh*cm)*P[n][m]/(cx||1e-12);
      Zp+=-(n+1)*fr*(gg*cm+hh*sm)*P[n][m];
    }
  }
  const psi=phiP-phi;
  const X=Xp*Math.cos(psi)-Zp*Math.sin(psi), Y=Yp;
  return Math.atan2(Y,X)*180/Math.PI;
}
