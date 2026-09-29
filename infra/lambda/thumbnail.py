import os, io, json
import boto3
from PIL import Image

ENDPOINT = os.getenv("AWS_ENDPOINT_URL", "http://floci:4566")
REGION = os.getenv("AWS_REGION", "us-east-1")

def lambda_handler(event, context=None):
    s3 = boto3.client("s3", region_name=REGION, endpoint_url=ENDPOINT,
        aws_access_key_id="test", aws_secret_access_key="test")
    pid = str(event["producto_id"])
    b_orig = event["bucket_original"]; k_orig = event["key_original"]
    b_thumb = event["bucket_thumb"]; k_thumb = event["key_thumb"]  # determinista thumbs/{id}.jpg
    try:
        obj = s3.get_object(Bucket=b_orig, Key=k_orig)
        data = obj["Body"].read()
    except Exception as e:
        return {"ok": False, "error": f"sin original: {e}"}
    try:
        img = Image.open(io.BytesIO(data))
        img.thumbnail((300, 300))  # proporcional, ej 1200x800 -> 300x200
        buf = io.BytesIO()
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf_size = img.size
        img.save(buf, format="JPEG")
        buf.seek(0)
        s3.put_object(Bucket=b_thumb, Key=k_thumb, Body=buf.getvalue(), ContentType="image/jpeg")
        return {"ok": True, "thumb": k_thumb, "size": buf_size}
    except Exception as e:
        return {"ok": False, "error": f"imagen inválida: {e}"}
