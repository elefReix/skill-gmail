---
name: gmail-default-organization
description: Configura la estructura de etiquetas (carpetas) por default recomendada para organizar Gmail y clasifica los correos existentes sin leer dentro de esas etiquetas. Úsalo cuando el usuario pida "organizar mi Gmail", "poner orden en mis correos", "crear carpetas para mi correo" o cualquier variante de limpiar/estructurar su bandeja de entrada desde cero. No renombra ni toca carpetas que el usuario ya tenga (p. ej. "Viajes") a menos que se indique explícitamente.
---

# Organización por default de Gmail

Este skill crea la estructura base de etiquetas de Gmail y clasifica los correos sin leer existentes dentro de ellas.

## Estructura por default

Al ejecutar este skill, crea (si no existen) las siguientes etiquetas usando `Gmail:create_label`:

| Etiqueta | Qué agrupa |
|---|---|
| Finanzas | Bancos, Afores, servicios financieros, telecom con cobros |
| Promociones | Ofertas, marketing, delivery, rentas, tiendas |
| Streaming | Netflix, Disney+, y similares |
| Newsletters | Boletines informativos, blogs, digests |
| LinkedIn - Social | Notificaciones sociales (reacciones, vistas de perfil, mensajes) |
| Seguridad | Alertas de seguridad de cuentas — NUNCA archivar/omitir bandeja automáticamente |
| Auto | Correos de agencias/servicio automotriz |

**Importante**: nunca modifiques, renombres ni muevas una etiqueta/carpeta que el usuario ya tenga creada (ejemplo conocido: "Viajes"), a menos que el usuario lo pida explícitamente en este turno.

## Pasos

1. Llama a `Gmail:list_labels` para ver qué etiquetas ya existen y evitar duplicados.
2. Crea las etiquetas faltantes de la tabla con `Gmail:create_label`.
3. Llama a `Gmail:search_threads` con `query: "is:unread in:inbox"` para traer los correos sin leer (usa `pageSize: 30` y pagina con `pageToken` si el usuario quiere cubrir más).
4. Clasifica cada hilo por el dominio del remitente o palabras clave del asunto, siguiendo esta guía de mapeo:
   - `accounts.google.com` + "alerta de seguridad" → Seguridad
   - Bancos/afores/telecom (profuturo, totalplay, etc.) → Finanzas
   - Netflix, Disney+ → Streaming
   - LinkedIn con asunto tipo "Daily", "Update", boletín → Newsletters
   - LinkedIn con asunto de reacciones/vistas de perfil/mensajes → LinkedIn - Social
   - Substack, Stack Overflow, Skool, blogs → Newsletters
   - Uber, delivery, tiendas, rentas de autos, eventos → Promociones
   - Agencias automotrices (Kia, etc.) → Auto
5. Aplica la etiqueta correspondiente a cada hilo con `Gmail:label_thread`.
6. Al terminar, resume al usuario cuántos correos quedaron en cada categoría y aclara que las herramientas disponibles no permiten crear **reglas de filtro automáticas** (esas se configuran manualmente en Gmail → Configuración → Filtros). Ofrece la sintaxis de búsqueda de Gmail lista para pegar en cada filtro.

## Notas

- Este skill es solo para la clasificación inicial/manual de correos ya existentes. Para automatizar la clasificación de correos futuros de un remitente específico, usa el skill `gmail-auto-move-sender`.
- Si el usuario quiere renombrar alguna de estas etiquetas después, usa el skill `gmail-rename-label`.
