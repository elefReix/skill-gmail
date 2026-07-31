---
name: gmail-view-label
description: Entra a una carpeta/etiqueta específica de Gmail y muestra los correos más recientes recibidos ahí (remitente y asunto). Úsalo cuando el usuario pida "entra a la carpeta X", "qué hay en la etiqueta Y", "muéstrame los últimos correos de la carpeta Z", o "dame un vistazo rápido de una carpeta en particular".
---

# Ver contenido reciente de una carpeta de Gmail

## Pasos

1. Si el nombre de la carpeta que menciona el usuario no es exacto o hay ambigüedad, llama a `Gmail:list_labels` para confirmar el nombre/`labelId` correcto antes de buscar.
2. Llama a `Gmail:search_threads` con:
   - `query: "label:<nombre-o-id> in:anywhere"` (usa `in:anywhere` para no perder correos que estén archivados fuera de INBOX)
   - `pageSize: 5` — por default solo se piden los 5 más recientes, salvo que el usuario pida más.
   - Los resultados de `search_threads` ya vienen ordenados del más reciente al más antiguo, así que no hace falta ordenar manualmente.
3. Por cada hilo, extrae `sender`, `subject` y `date` del mensaje (o del último mensaje del hilo si tiene varios).
4. Presenta la lista en una tabla simple, ejemplo:

   | Fecha | Remitente | Asunto |
   |---|---|---|
   | 30 jul, 22:47 | newsletters-noreply@linkedin.com | TechCrunch Daily: July 30, 2026 |

5. Si el usuario pide "los últimos 5" pero la carpeta tiene menos de 5 correos, muestra los que haya y acláralo.
6. Si el usuario quiere ver el contenido completo de alguno de esos correos, ofrécele usar `Gmail:get_thread` con el `id` del hilo correspondiente.

## Notas

- Este skill es de solo lectura — no aplica ni quita etiquetas, no archiva ni mueve nada.
- Si el usuario quiere un conteo total o un desglose por remitente en vez de los últimos 5, redirígelo al skill `gmail-list-recipients`.
