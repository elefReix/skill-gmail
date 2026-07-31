---
name: gmail-auto-move-sender
description: Mueve todos los correos existentes de un remitente (from:) específico a una carpeta/etiqueta de Gmail, y deja lista la regla de filtro para que los correos futuros de ese remitente se clasifiquen ahí automáticamente. Úsalo cuando el usuario pida "mueve los correos de X a la carpeta Y", "que todo lo de este remitente se vaya a la carpeta Z automáticamente", o "crea una regla para clasificar correos de un remitente".
---

# Mover remitente a una carpeta (retroactivo + automático a futuro)

## Limitación importante

El conector de Gmail disponible **no incluye una herramienta para crear reglas de filtro automáticas** (las que Gmail aplica solo a correos nuevos, sin intervención). Ese tipo de regla solo se puede crear manualmente desde Gmail → Configuración → Filtros y direcciones bloqueadas. Este skill hace la parte que sí es posible por API (clasificar lo existente) y te deja lista la sintaxis exacta para pegar en el filtro manual.

## Pasos

1. Confirma con el usuario: el remitente exacto (dominio o dirección) y el nombre de la carpeta/etiqueta destino.
2. Si la etiqueta destino no existe, créala con `Gmail:create_label` (o usa el skill `gmail-create-label`).
3. Busca todos los correos existentes de ese remitente: `Gmail:search_threads` con `query: "from:<remitente> in:anywhere"`. Usa `pageSize: 50` y pagina si `resultCountEstimate` es mayor a lo ya traído.
4. Aplica la etiqueta destino a cada hilo encontrado con `Gmail:label_thread`.
5. Pregunta al usuario si además quiere que esos correos se saquen de la bandeja de entrada (archivarlos): si sí, quita la etiqueta `INBOX` con `Gmail:unlabel_thread`.
6. Entrega al usuario el criterio exacto para crear el filtro automático manual, en este formato:

   > Ve a Gmail → ⚙️ Configuración → Ver toda la configuración → Filtros y direcciones bloqueadas → Crear un filtro nuevo.
   > En "De" pon: `<remitente>`
   > En el siguiente paso, marca "Aplicar la etiqueta: `<carpeta destino>`" y, si quiere que se archive solo, marca "Omitir la bandeja de entrada (Archivarlo)".

## Reglas importantes

- Nunca apliques esto a la carpeta/etiqueta "Viajes" ni a otras que el usuario haya marcado como protegidas, salvo que lo pida explícitamente en el turno actual.
- Para remitentes de alertas de seguridad o temas sensibles, no sugieras archivar automáticamente — recomienda dejarlos visibles en la bandeja.
- Si el volumen de correos del remitente es muy alto (cientos), avisa al usuario antes de procesar y pregunta si prefiere hacerlo en lotes.
