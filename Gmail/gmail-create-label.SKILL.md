---
name: gmail-create-label
description: Crea una nueva carpeta/etiqueta en Gmail, incluyendo etiquetas anidadas (subcarpetas). Úsalo cuando el usuario pida "crea una carpeta nueva en Gmail", "agrega una etiqueta llamada X", o quiera ampliar su estructura de organización con una categoría que no existe todavía.
---

# Crear carpeta (etiqueta) nueva en Gmail

## Pasos

1. Confirma con el usuario el nombre exacto de la carpeta/etiqueta que quiere crear. Si quiere que sea una subcarpeta de una ya existente, usa el formato `Carpeta padre/Subcarpeta` (Gmail crea la jerarquía automáticamente).
2. Llama a `Gmail:list_labels` para verificar que no exista ya una etiqueta con ese nombre (evita duplicados o nombres muy parecidos).
3. Crea la etiqueta con `Gmail:create_label`, pasando `displayName` con el nombre confirmado. Si es anidada, deja `autoCreateParentLabels` en su valor por default (true) salvo que el usuario indique lo contrario.
4. Confirma al usuario que la etiqueta fue creada y pregunta si quiere:
   - Clasificar correos existentes ahí (usa el skill `gmail-auto-move-sender` o `gmail-default-organization` según el caso).
   - Dejar la regla de filtro automática lista para correos futuros (dale la sintaxis de Gmail → Filtros, igual que en `gmail-auto-move-sender`).

## Notas

- No asignes un color a la etiqueta a menos que el usuario lo pida explícitamente.
- Si el usuario pide una carpeta con un nombre que ya existe, avísale en vez de crear un duplicado.
