---
name: gmail-rename-label
description: Renombra una etiqueta (carpeta) existente de Gmail. Úsalo cuando el usuario pida "renombrar una carpeta/etiqueta de Gmail", "cambiar el nombre de la carpeta X a Y", o quiera reorganizar el nombre de una categoría ya creada en su correo.
---

# Renombrar etiqueta de Gmail

## Pasos

1. Llama a `Gmail:list_labels` para obtener el `labelId` de la etiqueta que el usuario quiere renombrar. Búscala por coincidencia de nombre (ignora mayúsculas/acentos si es necesario) y confírmala con el usuario si hay ambigüedad.
2. Gmail no expone una herramienta directa de "renombrar" en este conector — renombrar equivale a **crear la nueva etiqueta y migrar los correos**:
   a. Crea la nueva etiqueta con `Gmail:create_label` usando el nombre nuevo. Si la etiqueta original es anidada (contiene "/"), conserva la misma jerarquía en el nuevo nombre.
   b. Busca todos los hilos con la etiqueta vieja: `Gmail:search_threads` con `query: "label:<id-o-nombre-de-la-etiqueta-vieja>"`.
   c. Para cada hilo, aplica la etiqueta nueva con `Gmail:label_thread` y quita la vieja con `Gmail:unlabel_thread`.
3. Informa al usuario que la etiqueta vieja quedó vacía y pregúntale si quiere que la elimines (este conector no incluye una herramienta de borrado de etiquetas; si no está disponible, indícale que puede borrarla manualmente desde Gmail → Configuración → Etiquetas, ya que quedará sin correos).

## Reglas importantes

- Nunca renombres o toques la carpeta/etiqueta "Viajes" (o cualquier otra que el usuario marque como protegida) salvo que lo pida explícitamente en el turno actual.
- Si la etiqueta tiene muchos correos (cientos), avisa al usuario que el proceso puede tardar varios pasos y pregunta si prefiere continuar o hacerlo en lotes.
- Confirma siempre el nombre nuevo con el usuario antes de crear la etiqueta, para evitar typos.
