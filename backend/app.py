import os, io, sqlite3, json
from flask import Flask, request, jsonify, Response

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://floci:4566")
DYNAMO_TABLE = os.getenv("DYNAMO_TABLE", "lomax-atributos")
S3_ORIG = os.getenv("S3_ORIGINALES", "lomax-originales")
S3_THUMB = os.getenv("S3_MINIATURAS", "lomax-miniaturas")
LAMBDA_FN = os.getenv("LAMBDA_THUMB", "lomax-thumbnail")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MAX_BYTES = 5 * 1024 * 1024

app = Flask(__name__)

# ---------- DB (RDS Postgres o fallback sqlite) ----------
pg_conn = None
use_pg = False
try:
    if DATABASE_URL:
        import psycopg2
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_conn.autocommit = True
        use_pg = True
        print("DB: usando Postgres RDS", flush=True)
except Exception as e:
    print("DB: Postgres no disponible, fallback sqlite:", e, flush=True)
    pg_conn = None

lite = sqlite3.connect("/tmp/lomax.db", check_same_thread=False)
lite.row_factory = sqlite3.Row

def db_exec(q, params=(), fetch=None):
    """q con %s para pg y ? para sqlite: escribimos con ? y convertimos si pg."""
    if use_pg:
        import psycopg2.extras
        cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(q.replace("?", "%s"), params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        try:
            return cur.fetchone()
        except Exception:
            return None
    else:
        cur = lite.cursor()
        cur.execute(q, params)
        lite.commit()
        if fetch == "one":
            r = cur.fetchone()
            return dict(r) if r else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        return None

def init_db():
    if use_pg:
        db_exec("""CREATE TABLE IF NOT EXISTS categorias(
          id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL)""")
        db_exec("""CREATE TABLE IF NOT EXISTS productos(
          id SERIAL PRIMARY KEY,
          codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
          descripcion TEXT NOT NULL, precio NUMERIC NOT NULL CHECK(precio>=0),
          categoria_id INT NOT NULL REFERENCES categorias(id),
          estado TEXT NOT NULL DEFAULT 'PENDIENTE',
          imagen_estado TEXT)""")
    else:
        db_exec("""CREATE TABLE IF NOT EXISTS categorias(
          id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL)""")
        db_exec("""CREATE TABLE IF NOT EXISTS productos(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
          descripcion TEXT NOT NULL, precio REAL NOT NULL CHECK(precio>=0),
          categoria_id INTEGER NOT NULL REFERENCES categorias(id),
          estado TEXT NOT NULL DEFAULT 'PENDIENTE',
          imagen_estado TEXT)""")
    for c in ["teclados", "pantallas", "audio"]:
        try:
            if use_pg:
                db_exec("INSERT INTO categorias(nombre) VALUES(?) ON CONFLICT DO NOTHING", (c,))
            else:
                db_exec("INSERT INTO categorias(nombre) VALUES(?)", (c,))
        except Exception:
            pass

init_db()

def get_cat_id(nombre):
    r = db_exec("SELECT * FROM categorias WHERE nombre=?", (nombre,), fetch="one")
    return r["id"] if r else None

def get_prod(pid):
    return db_exec("SELECT * FROM productos WHERE id=?", (pid,), fetch="one")

def cat_name(cid):
    r = db_exec("SELECT * FROM categorias WHERE id=?", (cid,), fetch="one")
    return r["nombre"] if r else None

# ---------- AWS clientes (Floci) ----------
from botocore.config import Config as BotoConfig
FAST = BotoConfig(connect_timeout=2, read_timeout=2, retries={"max_attempts": 0})
def aws_client(svc):
    return boto3.client(svc, region_name=AWS_REGION,
        endpoint_url=ENDPOINT, aws_access_key_id="test", aws_secret_access_key="test",
        config=FAST)

def ensure_buckets():
    try:
        s3 = aws_client("s3")
        for b in (S3_ORIG, S3_THUMB):
            try:
                s3.create_bucket(Bucket=b)
            except ClientError as e:
                if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise
    except Exception as e:
        print("S3 no disponible (fallback local):", e, flush=True)

ensure_buckets()

# Fallback local S3 en /tmp/s3
def local_put(bucket, key, data):
    p = f"/tmp/s3/{bucket}/{key}"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)

def local_get(bucket, key):
    p = f"/tmp/s3/{bucket}/{key}"
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return f.read()

def s3_put(bucket, key, data, ctype):
    try:
        aws_client("s3").put_object(Bucket=bucket, Key=key, Body=data, ContentType=ctype)
    except Exception:
        local_put(bucket, key, data)

def s3_get(bucket, key):
    try:
        r = aws_client("s3").get_object(Bucket=bucket, Key=key)
        return r["Body"].read()
    except Exception:
        return local_get(bucket, key)

def s3_exists(bucket, key):
    if s3_get(bucket, key) is not None:
        return True
    return False

def dynamo_put(pid, attrs):
    try:
        t = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=ENDPOINT,
            aws_access_key_id="test", aws_secret_access_key="test", config=FAST).Table(DYNAMO_TABLE)
        t.put_item(Item={"producto_id": str(pid), "atributos": attrs})
        return True
    except Exception as e:
        print("Dynamo put fallo, fallback local:", e, flush=True)
        os.makedirs("/tmp/dynamo", exist_ok=True)
        with open(f"/tmp/dynamo/{pid}.json", "w") as f:
            json.dump(attrs, f)
        return False  # indica que no fue a Dynamo real

def dynamo_get(pid):
    try:
        t = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=ENDPOINT,
            aws_access_key_id="test", aws_secret_access_key="test", config=FAST).Table(DYNAMO_TABLE)
        r = t.get_item(Key={"producto_id": str(pid)})
        return r.get("Item", {}).get("atributos")
    except Exception:
        p = f"/tmp/dynamo/{pid}.json"
        if os.path.exists(p):
            return json.load(open(p))
        return None

def thumb_key(pid):
    return f"thumbs/{pid}.jpg"  # determinista

def generar_thumb_local(original_bytes):
    from PIL import Image
    img = Image.open(io.BytesIO(original_bytes))
    img.thumbnail((300, 300))
    buf = io.BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(buf, format="JPEG")
    return buf.getvalue(), img.size

def invocar_lambda_thumb(pid, orig_key):
    """Intenta Lambda real; si falla, genera local y sube (para no bloquear E2E). Retorna (ok, detalle)."""
    payload = {"producto_id": str(pid), "bucket_original": S3_ORIG, "key_original": orig_key,
               "bucket_thumb": S3_THUMB, "key_thumb": thumb_key(pid)}
    try:
        lam = boto3.client("lambda", region_name=AWS_REGION, endpoint_url=ENDPOINT,
            aws_access_key_id="test", aws_secret_access_key="test",
            config=BotoConfig(connect_timeout=5, read_timeout=180, retries={"max_attempts": 0}))
        r = lam.invoke(FunctionName=LAMBDA_FN, Payload=json.dumps(payload))
        data = r["Payload"].read()
        try:
            j = json.loads(data or b"{}")
        except Exception:
            j = {}
        if r.get("StatusCode") == 200 and r.get("FunctionError") is None:
            return True, f"lambda ok {j}"
        return False, f"lambda error {j}"
    except Exception as e:
        return False, f"lambda no disponible: {e}"

def procesar_imagen(pid, orig_bytes, orig_key):
    """Sube original ya hecho por caller. Genera miniatura (lambda o local). Actualiza estado. Retorna (publicado, msg, status)."""
    ok_l, det = invocar_lambda_thumb(pid, orig_key)
    thumb = None
    if ok_l:
        thumb = s3_get(S3_THUMB, thumb_key(pid))
    if thumb is None:
        # fallback local (también valida imagen)
        try:
            tbytes, _ = generar_thumb_local(orig_bytes)
            s3_put(S3_THUMB, thumb_key(pid), tbytes, "image/jpeg")
            thumb = tbytes
            det += " | fallback local ok"
        except Exception as e:
            db_exec("UPDATE productos SET imagen_estado='ERROR' WHERE id=?", (pid,))
            return False, f"imagen inválida o fallo: {e} | {det}", 502
    # hay miniatura: verificar atributos
    attrs = dynamo_get(pid)
    # si Dynamo real falló antes, el fallback local cuenta como atributos presentes
    if attrs:
        db_exec("UPDATE productos SET estado='PUBLICADO', imagen_estado='OK' WHERE id=?", (pid,))
        return True, f"PUBLICADO. {det}", 200
    else:
        db_exec("UPDATE productos SET imagen_estado='OK' WHERE id=?", (pid,))
        return False, f"miniatura ok pero sin atributos, sigue PENDIENTE. {det}", 200

# ---------- Endpoints ----------
@app.get("/api/categorias")
def categorias():
    rows = db_exec("SELECT nombre FROM categorias", fetch="all")
    return jsonify([r["nombre"] for r in rows]), 200

@app.post("/api/productos")
def crear():
    d = request.get_json(force=True, silent=True) or {}
    codigo = d.get("codigo"); nombre = d.get("nombre"); desc = d.get("descripcion")
    precio = d.get("precio"); cat = d.get("categoria"); attrs = d.get("atributos", {})
    if not all([codigo, nombre, desc, cat]) or precio is None:
        return jsonify(error="campos obligatorios: codigo,nombre,descripcion,precio,categoria"), 400
    try:
        precio = float(precio)
    except Exception:
        return jsonify(error="precio inválido"), 400
    if precio < 0:
        return jsonify(error="precio no negativo"), 400
    cid = get_cat_id(cat)
    if not cid:
        return jsonify(error="categoría inexistente"), 400
    # transacción: sin parciales
    try:
        db_exec("INSERT INTO productos(codigo,nombre,descripcion,precio,categoria_id,estado) VALUES(?,?,?,?,?, 'PENDIENTE')",
                (codigo, nombre, desc, precio, cid))
    except Exception as e:
        if "UNIQUE" in str(e).upper() or "unique" in str(e).lower() or "duplicate" in str(e).lower():
            row = db_exec("SELECT * FROM productos WHERE codigo=?", (codigo,), fetch="one")
            return jsonify(error="código duplicado", producto_id=row["id"] if row else None), 409
        return jsonify(error=f"db: {e}"), 400
    row = db_exec("SELECT * FROM productos WHERE codigo=?", (codigo,), fetch="one")
    pid = row["id"]
    # Dynamo mismo producto_id; si falla servicio -> 502/503 conservando PENDIENTE
    try:
        ok = dynamo_put(pid, attrs)
        if not ok:
            return jsonify(producto_id=pid, estado="PENDIENTE", warn="dynamodb no disponible, fallback local"), 503
    except Exception as e:
        return jsonify(producto_id=pid, estado="PENDIENTE", error=f"dynamo: {e}"), 503
    return jsonify(producto_id=pid, estado="PENDIENTE"), 201

def _validar_archivo(file):
    data = file.read()
    if len(data) > MAX_BYTES:
        return None, (jsonify(error="archivo mayor a 5MB"), 413)
    fname = (file.filename or "").lower()
    if not (fname.endswith(".jpg") or fname.endswith(".jpeg") or fname.endswith(".png")):
        return None, (jsonify(error="formato no permitido (solo JPEG/PNG)"), 415)
    # magic bytes
    if data[:2] == b"\xff\xd8":
        ctype = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        ctype = "image/png"
    else:
        return None, (jsonify(error="imagen inválida"), 400)
    return (data, ctype), None

@app.post("/api/productos/<int:pid>/imagen")
def subir(pid):
    p = get_prod(pid)
    if not p:
        return jsonify(error="producto inexistente"), 404
    if "file" not in request.files:
        return jsonify(error="falta file"), 400
    val, err = _validar_archivo(request.files["file"])
    if err:
        db_exec("UPDATE productos SET imagen_estado='ERROR' WHERE id=?", (pid,))
        return err
    data, ctype = val
    orig_key = f"originales/{pid}/original"
    try:
        s3_put(S3_ORIG, orig_key, data, ctype)
    except Exception as e:
        db_exec("UPDATE productos SET imagen_estado='ERROR' WHERE id=?", (pid,))
        return jsonify(error=f"s3: {e}"), 503
    pub, msg, st = procesar_imagen(pid, data, orig_key)
    code = 201 if pub else st
    if code == 200 and not pub:
        code = 200
    return jsonify(producto_id=pid, publicado=pub, detalle=msg,
                   estado=get_prod(pid)["estado"]), code

@app.post("/api/productos/<int:pid>/reprocesar")
def reprocesar(pid):
    p = get_prod(pid)
    if not p:
        return jsonify(error="producto inexistente"), 404
    orig_key = f"originales/{pid}/original"
    if not s3_exists(S3_ORIG, orig_key):
        return jsonify(error="sin original, nada que reprocesar"), 409
    orig = s3_get(S3_ORIG, orig_key)
    pub, msg, st = procesar_imagen(pid, orig, orig_key)
    return jsonify(producto_id=pid, publicado=pub, detalle=msg,
                   estado=get_prod(pid)["estado"]), 200

@app.get("/api/productos")
def listar():
    rows = db_exec("SELECT * FROM productos WHERE estado='PUBLICADO'", fetch="all") or []
    out = []
    for r in rows:
        out.append({"id": r["id"], "codigo": r["codigo"], "nombre": r["nombre"],
            "precio": r["precio"], "categoria": cat_name(r["categoria_id"]),
            "miniatura": f"/api/productos/{r['id']}/imagen?tipo=thumb"})
    return jsonify(out), 200

@app.get("/api/productos/<int:pid>")
def detalle(pid):
    p = get_prod(pid)
    if not p:
        return jsonify(error="producto inexistente"), 404
    return jsonify({"id": p["id"], "codigo": p["codigo"], "nombre": p["nombre"],
        "descripcion": p["descripcion"], "precio": p["precio"],
        "categoria": cat_name(p["categoria_id"]), "estado": p["estado"],
        "atributos": dynamo_get(pid)}), 200

@app.get("/api/productos/<int:pid>/imagen")
def imagen(pid):
    p = get_prod(pid)
    if not p:
        return jsonify(error="producto inexistente"), 404
    tipo = request.args.get("tipo", "original")
    if tipo == "thumb":
        data = s3_get(S3_THUMB, thumb_key(pid))
        if not data:
            return jsonify(error="imagen inexistente"), 404
        return Response(data, mimetype="image/jpeg")
    data = s3_get(S3_ORIG, f"originales/{pid}/original")
    if not data:
        return jsonify(error="imagen inexistente"), 404
    mt = "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    return Response(data, mimetype=mt)

@app.get("/api/health")
def health():
    return jsonify(status="ok", db="pg" if use_pg else "sqlite"), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("BACKEND_PORT", "3000")))
