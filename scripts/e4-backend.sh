#!/bin/bash
set -e
B=${API:-http://proxy/api}
echo "GET categorias:"; curl -s $B/categorias; echo
echo "POST válido:"; curl -s -X POST $B/productos -H 'Content-Type: application/json' -d '{"codigo":"T001","nombre":"Teclado X","descripcion":"mecánico","precio":99.9,"categoria":"teclados","atributos":{"switch":"blue"}}'; echo
echo "POST duplicado (409):"; curl -s -o /dev/null -w '%{http_code}\n' -X POST $B/productos -H 'Content-Type: application/json' -d '{"codigo":"T001","nombre":"Dup","descripcion":"x","precio":10,"categoria":"teclados"}'
echo "POST precio negativo (400):"; curl -s -o /dev/null -w '%{http_code}\n' -X POST $B/productos -H 'Content-Type: application/json' -d '{"codigo":"NEG1","nombre":"N","descripcion":"x","precio":-5,"categoria":"teclados"}'
echo "POST categoría inexistente (400):"; curl -s -o /dev/null -w '%{http_code}\n' -X POST $B/productos -H 'Content-Type: application/json' -d '{"codigo":"X1","nombre":"N","descripcion":"x","precio":5,"categoria":"noexiste"}'
echo "GET productos:"; curl -s $B/productos; echo
