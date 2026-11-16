#!/usr/bin/env python3
"""Baja el catálogo con precios de elgasolero.com y genera catalogo.json para la app.

Uso:  ELGASOLERO_CLAVE=... python3 sync_catalogo.py [catalogo.json] [estado.json]
- Entra con la clave del catálogo (campo "clave_local"), pide TODOS los productos (rub=99999) y los lee.
- Si algo sale raro (clave cambiada, página distinta, muy pocos productos) termina con error, NO toca el catálogo
  y deja el motivo en estado.json para que la app avise.
- Si los precios no cambiaron, no reescribe catalogo.json (así no se llena el repo de cambios).
"""
import os,re,sys,json,html as H,time
import requests
from bs4 import BeautifulSoup

BASE='https://www.elgasolero.com/'
UA={'User-Agent':'Mozilla/5.0 (compatible; SHR-catalogo-sync/1.0)'}
MIN_PRODUCTOS=1500            # el catálogo real tiene ~3.000: menos que esto = algo falló
MAX_CAIDA=0.35                # si de golpe faltan más del 35 % de los productos anteriores, no se actualiza

def fix(s):
    """La página mezcla codificaciones: arregla los textos doblemente codificados (Ã‘ -> Ñ)."""
    s=H.unescape(s or '').replace('\xa0',' ')
    if re.search('[ÃÂ]',s):
        try:s=s.encode('latin-1').decode('utf-8')
        except Exception:s=s.replace('Ã‘','Ñ').replace('Ã±','ñ').replace('Â°','°')
    return re.sub(r'\s+',' ',s).strip()

def precio(txt):
    m=re.search(r'\$\s*([\d.]+)(?:,(\d+))?',txt or '')
    if not m:return None
    n=float(m.group(1).replace('.','')+('.'+m.group(2) if m.group(2) else ''))
    return int(n) if n==int(n) else n

def parse(html_text):
    soup=BeautifulSoup(html_text,'lxml') if _lxml() else BeautifulSoup(html_text,'html.parser')
    out,seen={},0
    for box in soup.select('div.caja_producto'):
        t=box.get_text(' ',strip=True)
        m=re.search(r'Cód\.:\s*(\S+)',t)
        if not m:continue
        seen+=1
        c=m.group(1).strip()
        h1=box.find('h1');n=fix(h1.get_text(' ')) if h1 else ''
        r=box.select_one('p.rubro_centrado');r=fix(r.get_text(' ')) if r else ''
        pb=re.search(r'Cant\.\s*p/bulto:?\s*([\d.,]+)',t);b=None
        if pb:
            try:b=int(float(pb.group(1).replace('.','').replace(',','.')))
            except Exception:b=None
        pe=box.select_one('.precio-numero');p=precio(pe.get_text(' ')) if pe else None
        fotos=len({i.get('src') for i in box.select('.carousel-inner img') if i.get('src')})
        if not n or p is None:continue
        out[c]={'c':c,'n':n,'r':r,'p':p,'b':b,'f':fotos}
    return list(out.values()),seen

def _lxml():
    try:import lxml;return True
    except Exception:return False

def login(clave):
    s=requests.Session();s.headers.update(UA)
    r=s.post(BASE+'catalogo2024_publico.php',data={'clave_local':clave},timeout=60)
    r.raise_for_status()
    return s

def decodificar(resp):
    b=resp.content
    try:return b.decode('utf-8')
    except UnicodeDecodeError:return b.decode('cp1252',errors='replace')

def falla(estado,msg):
    json.dump({'ok':False,'error':msg,'fecha':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},open(estado,'w',encoding='utf-8'),ensure_ascii=False)
    sys.exit('ERROR: '+msg)

def main():
    clave=os.environ.get('ELGASOLERO_CLAVE','').strip()
    salida=sys.argv[1] if len(sys.argv)>1 else 'catalogo.json'
    estado=sys.argv[2] if len(sys.argv)>2 else 'estado.json'
    if not clave:falla(estado,'Falta la clave de elgasolero.com (secreto ELGASOLERO_CLAVE en GitHub).')
    try:
        s=login(clave)
        for intento in range(3):
            r=s.get(BASE+'catalogo2024.php?rub=99999',timeout=300)
            texto=decodificar(r)
            if r.status_code==200 and 'No tienes acceso' not in texto:break
            time.sleep(5)
    except Exception as e:
        falla(estado,'No pude conectar con elgasolero.com: %s'%e)
    if 'No tienes acceso' in texto:
        falla(estado,'La clave de elgasolero.com ya no sirve. Hay que cargar la clave nueva en GitHub (secreto ELGASOLERO_CLAVE).')
    prods,seen=parse(texto)
    print(f'Leí {len(prods)} productos con precio ({seen} bloques).')
    if len(prods)<MIN_PRODUCTOS:falla(estado,f'Solo pude leer {len(prods)} productos: la página cambió o la clave no abrió el catálogo. No se actualizó nada.')
    prods.sort(key=lambda x:(x['r'],x['n'],x['c']))
    nuevo={'productos':[{k:v for k,v in x.items() if k!='f'} for x in prods],'fotos':{x['c']:x['f'] for x in prods if x['f']>1}}
    ahora=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    if os.path.exists(salida):
        try:
            ant=json.load(open(salida,encoding='utf-8'))
            n_ant=len(ant.get('productos',[]))
            if n_ant and len(prods)<n_ant*(1-MAX_CAIDA):falla(estado,f'Antes había {n_ant} productos y ahora {len(prods)}. No se actualizó nada, revisar.')
            if ant.get('productos')==nuevo['productos'] and ant.get('fotos')==nuevo['fotos']:
                print('Sin cambios de precios.')
                json.dump({'ok':True,'verificado':ahora,'productos':len(prods)},open(estado,'w',encoding='utf-8'));return
        except (ValueError,OSError):pass
    nuevo['actualizado']=ahora
    json.dump(nuevo,open(salida,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    json.dump({'ok':True,'verificado':ahora,'productos':len(prods)},open(estado,'w',encoding='utf-8'))
    print('Catálogo actualizado:',salida)
if __name__=='__main__':main()
