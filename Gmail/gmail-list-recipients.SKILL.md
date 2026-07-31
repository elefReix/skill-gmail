---
name: gmail-list-recipients
description: Lista los remitentes (o destinatarios) de los correos dentro de una etiqueta/carpeta específica de Gmail. Úsalo cuando el usuario pida "quién me ha escrito en la carpeta X", "lista los remitentes de la etiqueta Y", "qué contactos tengo en la carpeta Z", o quiera un resumen de quién aparece en una categoría de su correo.
---

# Listar remitentes de una carpeta de Gmail

## Pasos

1. Llama a `Gmail:list_labels` para confirmar el nombre exacto y el `labelId` de la carpeta/etiqueta que el usuario menciona.
2. Llama a `Gmail:search_threads` con `query: "label:<id-o-nombre>"` y `view: "THREAD_VIEW_METADATA_ONLY"` (más rápido, no necesitas el snippet). Usa `pageSize: 50` y pagina con `pageToken` si `resultCountEstimate` indica que hay más resultados de los que trajiste.
3. Extrae el campo `sender` (o `toRecipients` si el usuario pidió destinatarios) de cada hilo/mensaje.
4. Deduplica por dirección de correo y cuenta cuántos hilos hay por remitente.
5. Presenta al usuario una lista ordenada de mayor a menor frecuencia, por ejemplo:

   | Remitente | Correos en esta carpeta |
   |---|---|
   | uber@uber.com | 6 |
   | info@members.netflix.com | 3 |

6. Si el usuario quiere profundizar en un remitente en particular, ofrece usar `Gmail:get_thread` sobre uno de los hilos para ver el contenido completo.

## Notas

- Si la carpeta tiene cientos de correos, aclara al usuario que el conteo es sobre la muestra traída (menciona `resultCountEstimate`) y ofrece traer más páginas si lo necesita.
- No expongas contenido completo de los correos en este listado — solo remitente/destinatario y conteo, salvo que el usuario pida detalle de un hilo específico.
