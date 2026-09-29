#!/bin/bash
set -e
B=${API:-http://proxy/api}
J=datos/productos/productos.json
python3 - "$B" "$J" <<'PY'
import json,sys,urllib.request,os
B,J=sys.argv[1],sys.argv[2]
items=json.load(open(J))
for it in items:
    body={k:it[k] for k in ("codigo","nombre","descripcion","precio","categoria","atributos")}
    req=urllib.request.Request(B+"/productos",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"},method="POST")
    try:
        r=urllib.request.urlopen(req); j=json.load(r); pid=j["producto_id"]
    except Exception as e:
        print("POST",it["codigo"],"->",e); continue
    print("POST",it["codigo"],"->",pid)
    fp="datos/imagenes/"+it["foto"]
    import http.client, mimetypes
    import subprocess
    subprocess.run(["curl","-s","-X","POST",f"{B}/productos/{pid}/imagen","-F",f"file=@{fp}"],check=False)
PY
echo "carga 20 finalizada. Verificar GET $B/productos"
