#!/usr/bin/env python3
"""Genera 20 JPG 1200x800 + inválido + >5MB en datos/imagenes (ejecutar en tools)."""
from PIL import Image
import os
os.makedirs("datos/imagenes", exist_ok=True)
cols=[(200,30,30),(30,120,200),(30,160,60)]*7
for i in range(1,21):
    im=Image.new("RGB",(1200,800),cols[i-1])
    im.save(f"datos/imagenes/p{i:02d}.jpg","JPEG",quality=85)
open("datos/imagenes/invalido.jpg","wb").write(b"esto no es imagen")
open("datos/imagenes/grande.jpg","wb").write(b"\xff\xd8"+b"\x00"*(6*1024*1024))
print("listo")
