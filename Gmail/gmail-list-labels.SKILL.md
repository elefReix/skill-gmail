---
name: gmail-list-labels
description: Lista todas las carpetas/etiquetas que existen en la cuenta de Gmail del usuario. Úsalo cuando el usuario pida "qué carpetas tengo en Gmail", "lista mis etiquetas", "muéstrame mis carpetas de correo", o quiera ver un panorama general de cómo tiene organizado su correo antes de crear, renombrar o entrar a una carpeta.
---

# Listar carpetas de Gmail

## Pasos

1. Llama a `Gmail:list_labels` (pagina con `pageToken` si hay más resultados de los que trae por default).
2. Separa el resultado en dos grupos para la respuesta:
   - **Etiquetas del sistema** (INBOX, SENT, TRASH, SPAM, STARRED, IMPORTANT, DRAFT, UNREAD, etc.) — menciónalas solo si el usuario las pide explícitamente; normalmente no son el foco.
   - **Etiquetas creadas por el usuario** — estas son las "carpetas" que le interesan.
3. Presenta la lista de etiquetas de usuario en una tabla simple, respetando la jerarquía si hay subcarpetas (ej. `Viajes/Vuelos`, `Viajes/Hoteles`).
4. Si el usuario quiere saber cuántos correos tiene cada una, ofrécele usar el skill `gmail-list-recipients` (que además de contar remitentes te da el conteo de hilos) o el skill `gmail-view-label` para ver el detalle de una carpeta puntual.

## Notas

- No expongas los `labelId` internos en la respuesta al usuario salvo que los pida — usa el nombre visible (`name`).
- Si la cuenta tiene muchas etiquetas anidadas, agrúpalas visualmente por carpeta padre para que sea fácil de leer.
