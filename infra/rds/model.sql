CREATE TABLE IF NOT EXISTS categorias(
  id SERIAL PRIMARY KEY, nombre TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS productos(
  id SERIAL PRIMARY KEY,
  codigo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
  descripcion TEXT NOT NULL, precio NUMERIC NOT NULL CHECK(precio>=0),
  categoria_id INT NOT NULL REFERENCES categorias(id),
  estado TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK(estado IN ('PENDIENTE','PUBLICADO')),
  imagen_estado TEXT CHECK(imagen_estado IN ('OK','ERROR')));
INSERT INTO categorias(nombre) VALUES ('teclados'),('pantallas'),('audio') ON CONFLICT DO NOTHING;
