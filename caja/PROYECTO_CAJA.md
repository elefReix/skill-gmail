# Proyecto CAJA — instrucciones de construcción

Cómo levantar el board `CAJA.exe` como aplicación real: **Ionic + Angular** en el front, **Supabase** en el back, con la **misma estructura de monorepo que `kaee-inventario`**.

El artefacto HTML que ya existe es la referencia funcional y visual. Este documento traduce cada sección de ese board a pantallas, tablas y rutas.

---

## 1. Qué se va a construir

El board tiene cuatro secciones. Cada una es una ruta:

| Sección del board | Ruta | Qué hace |
|---|---|---|
| Resumen | `/` | Entradas, salidas, balance y margen del periodo. Desglose por categoría y últimos movimientos. |
| Entradas | `/entradas` | Alta de ingresos (ventas y sueldo). Tabla filtrable por categoría y forma de cobro. |
| Salidas | `/salidas` | Alta de compras con proveedor, categoría y tarjeta. Tabla filtrable + gasto por tarjeta. |
| Catálogo | `/catalogo` | Alta y baja de proveedores, formas de pago y categorías. |

Reglas de negocio que ya están resueltas en el board y hay que conservar:

- **Una categoría tiene tipo**: `entrada`, `salida` o `ambas`. Los selectores de cada formulario solo ofrecen las categorías compatibles.
- **Borrar del catálogo no borra movimientos.** El movimiento se queda y muestra "sin asignar". En SQL esto es `on delete set null`, no `cascade`.
- **El periodo es mensual** y filtra todo lo que se ve.
- **Borrado en dos pasos** en la UI: el primer clic arma, el segundo confirma.

---

## 2. Stack

Versiones exactas tomadas de `kaee-inventario/package.json`. Fijar las mismas evita pelearse con diferencias de API entre versiones.

| Pieza | Versión |
|---|---|
| Nx | `23.1.0` |
| Angular | `22.0.6` |
| Ionic Angular | `^8.8.16` |
| Capacitor | `^8.5.0` (core, cli, android) |
| supabase-js | `^2.112.0` |
| NestJS (app `api`) | `^11.0.0` |
| TypeScript | `6.0.3` |
| ionicons | `^8.1.0` |
| Jest | `~30.3.0` + `jest-preset-angular ~17.0.0` |
| Playwright | `^1.36.0` |

Node 24 en CI.

---

## 3. Estructura del monorepo

Espejo de kaee:

```
caja/
├── apps/
│   ├── web/                    # Angular 22 + Ionic 8 (standalone)
│   │   ├── android/            # Capacitor
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── core/       # servicios y guards transversales
│   │   │   │   ├── features/   # una carpeta por pantalla
│   │   │   │   ├── app.config.ts
│   │   │   │   ├── app.routes.ts
│   │   │   │   └── app.ts
│   │   │   ├── environments/
│   │   │   │   ├── environment.ts
│   │   │   │   └── environment.prod.ts
│   │   │   ├── main.ts
│   │   │   ├── styles.scss
│   │   │   └── test-setup.ts
│   │   ├── capacitor.config.ts
│   │   ├── jest.config.cts
│   │   ├── project.json
│   │   ├── proxy.conf.json
│   │   └── tsconfig.{app,spec}.json
│   ├── web-e2e/                # Playwright
│   ├── api/                    # NestJS — solo si necesitas lógica de servidor
│   └── api-e2e/
├── packages/
│   ├── shared/models/          # @org/models — tipos compartidos
│   └── caja/
│       ├── data/               # @org/caja/data — acceso a datos
│       └── shared-ui/          # @org/caja/shared-ui — componentes reutilizables
├── supabase/
│   └── migrations/             # <timestamp>_<nombre>.sql
├── tools/
├── .github/workflows/ci.yml
├── nx.json
├── tsconfig.base.json
├── eslint.config.mjs
├── jest.config.ts / jest.preset.js
└── package.json
```

### Sobre `apps/api`

kaee tiene una app NestJS. **Para CAJA probablemente no la necesitas**: PostgREST y las RPC de Supabase cubren todo lo del board, y `apps/web` habla directo con Supabase. Genera `api` solo cuando aparezca algo que no pueda vivir en el cliente (webhooks, integraciones con terceros, trabajos programados, un secreto que no puede salir del servidor).

Si la omites, quita también `"dependsOn": ["api:serve"]` del target `serve` de `apps/web/project.json`, o `nx serve web` fallará buscando un proyecto inexistente.

---

## 4. Fase 0 — crear el workspace

```bash
npx create-nx-workspace@23.1.0 caja --preset=apps --packageManager=npm
cd caja

npm i -D @nx/angular@23.1.0 @nx/playwright@23.1.0 @nx/jest@23.1.0 @nx/js@23.1.0
```

App web:

```bash
npx nx g @nx/angular:application apps/web \
  --style=scss \
  --routing=true \
  --standalone=true \
  --unitTestRunner=jest \
  --e2eTestRunner=playwright \
  --prefix=app
```

Ionic, Capacitor y Supabase:

```bash
npm i @ionic/angular@^8.8.16 ionicons@^8.1.0 @supabase/supabase-js@^2.112.0
npm i @capacitor/core@^8.5.0 @capacitor/android@^8.5.0 @capacitor/angular@^2.0.3
npm i -D @capacitor/cli@^8.5.0 @ionic/angular-toolkit@^12.3.0

npx cap init caja mx.caja.app --web-dir=../../dist/apps/web/browser
```

Librerías compartidas:

```bash
npx nx g @nx/js:library packages/shared/models --importPath=@org/models --unitTestRunner=none
npx nx g @nx/angular:library packages/caja/data --importPath=@org/caja/data
npx nx g @nx/angular:library packages/caja/shared-ui --importPath=@org/caja/shared-ui
```

### `styles.scss`

Copia tal cual el de kaee — son los imports que Ionic necesita para renderizar bien:

```scss
@import '@ionic/angular/css/core.css';
@import '@ionic/angular/css/normalize.css';
@import '@ionic/angular/css/structure.css';
@import '@ionic/angular/css/typography.css';
@import '@ionic/angular/css/display.css';
@import '@ionic/angular/css/padding.css';
@import '@ionic/angular/css/float-elements.css';
@import '@ionic/angular/css/text-alignment.css';
@import '@ionic/angular/css/text-transformation.css';
@import '@ionic/angular/css/flex-utils.css';
```

Debajo de esos imports va la paleta del board (verde neón sobre negro) como variables CSS y overrides de las variables de Ionic.

---

## 5. Fase 1 — Supabase

### 5.1 Proyecto y credenciales

Crea el proyecto en Supabase y guarda URL + anon key en los environments, igual que kaee:

```ts
// apps/web/src/environments/environment.ts
export const environment = {
  production: false,
  supabaseUrl: 'https://<tu-proyecto>.supabase.co',
  supabaseAnonKey: '<tu-publishable-key>',
};
```

`environment.prod.ts` con las mismas llaves y `production: true`. El swap lo hace el `fileReplacements` de la configuración `production` en `apps/web/project.json`.

> La anon/publishable key es pública por diseño — va en el bundle. Lo que protege los datos es RLS, no esconder la llave. La `service_role` key **nunca** entra al front.

### 5.2 Esquema

`supabase/migrations/<timestamp>_esquema_inicial.sql`:

```sql
-- Catálogo: proveedores, formas de pago y categorías.
-- Todo cuelga de auth.users para que RLS pueda aislar por usuario desde el día uno.

create table public.proveedores (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references auth.users (id) on delete cascade,
  nombre      text not null,
  nota        text,
  activo      boolean not null default true,
  creado_en   timestamptz not null default now()
);

create table public.formas_pago (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references auth.users (id) on delete cascade,
  nombre      text not null,
  -- Día del mes en que se paga la tarjeta. Null para efectivo o débito.
  dia_pago    smallint check (dia_pago between 1 and 31),
  activo      boolean not null default true,
  creado_en   timestamptz not null default now()
);

create table public.categorias (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references auth.users (id) on delete cascade,
  nombre      text not null,
  tipo        text not null check (tipo in ('entrada', 'salida', 'ambas')),
  activo      boolean not null default true,
  creado_en   timestamptz not null default now()
);

-- Movimientos: una sola tabla para entradas y salidas, distinguidas por `tipo`.
-- Separarlas en dos tablas duplicaría todas las consultas del resumen sin ganar nada:
-- las columnas son idénticas y siempre se leen juntas para calcular el balance.
create table public.movimientos (
  id             uuid primary key default gen_random_uuid(),
  usuario_id     uuid not null references auth.users (id) on delete cascade,
  tipo           text not null check (tipo in ('entrada', 'salida')),
  fecha          date not null,
  concepto       text not null,
  monto          numeric(12, 2) not null check (monto >= 0),
  -- on delete set null, no cascade: borrar algo del catálogo NO puede borrar
  -- movimientos ya registrados; el movimiento sobrevive como "sin asignar".
  categoria_id   uuid references public.categorias (id) on delete set null,
  proveedor_id   uuid references public.proveedores (id) on delete set null,
  forma_pago_id  uuid references public.formas_pago (id) on delete set null,
  -- Los clientes se capturan como texto libre; si algún día necesitan ficha
  -- propia, esto se migra a una tabla `clientes` con su FK.
  cliente        text,
  creado_en      timestamptz not null default now()
);

-- El resumen y las tablas siempre filtran por usuario + rango de fechas.
create index movimientos_usuario_fecha_idx
  on public.movimientos (usuario_id, fecha desc);
create index movimientos_usuario_tipo_fecha_idx
  on public.movimientos (usuario_id, tipo, fecha desc);
```

### 5.3 RLS

**Obligatorio antes de exponer nada.** Sin esto, la anon key deja leer toda la tabla:

```sql
alter table public.proveedores  enable row level security;
alter table public.formas_pago  enable row level security;
alter table public.categorias   enable row level security;
alter table public.movimientos  enable row level security;

-- Cada quien ve y modifica solo lo suyo.
create policy "propias" on public.proveedores
  for all using (auth.uid() = usuario_id) with check (auth.uid() = usuario_id);

create policy "propias" on public.formas_pago
  for all using (auth.uid() = usuario_id) with check (auth.uid() = usuario_id);

create policy "propias" on public.categorias
  for all using (auth.uid() = usuario_id) with check (auth.uid() = usuario_id);

create policy "propios" on public.movimientos
  for all using (auth.uid() = usuario_id) with check (auth.uid() = usuario_id);
```

### 5.4 RPC del resumen

kaee usa RPC cuando algo debe resolverse en una sola ida al servidor (ver `finalizar_entrada`). El resumen por categoría es el caso equivalente aquí: agregar en el cliente obligaría a bajar todos los movimientos del mes.

```sql
-- Totales por tipo y categoría en un rango. security invoker para que respete
-- las mismas policies RLS que ya aplican a la tabla — no abre una puerta lateral.
create or replace function public.resumen_periodo(p_desde date, p_hasta date)
returns table (
  tipo         text,
  categoria_id uuid,
  categoria    text,
  total        numeric,
  movimientos  bigint
)
language sql
security invoker
stable
as $$
  select
    m.tipo,
    m.categoria_id,
    coalesce(c.nombre, 'Sin categoría') as categoria,
    sum(m.monto)                        as total,
    count(*)                            as movimientos
  from public.movimientos m
  left join public.categorias c on c.id = m.categoria_id
  where m.fecha between p_desde and p_hasta
  group by m.tipo, m.categoria_id, c.nombre
  order by sum(m.monto) desc;
$$;

comment on function public.resumen_periodo is
  'Totales por tipo y categoría para el panel de resumen. security invoker: respeta las policies RLS de movimientos.';
```

Con eso el front calcula entradas, salidas, balance y margen sumando las filas que devuelve, sin traerse los movimientos.

Para el bloque "gasto por tarjeta" de la sección Salidas, una RPC gemela agrupando por `forma_pago_id`.

### 5.5 Semilla del catálogo

El board arranca con catálogo precargado. Replícalo en una migración aparte o en un trigger `on auth.users insert`, para que un usuario nuevo no empiece con selectores vacíos:

- **Categorías entrada**: Sueldo / nómina, Ventas mostrador, Ventas en línea, Servicios prestados
- **Categorías salida**: Inventario, Servicios (luz, agua, internet), Suscripciones, Transporte, Impuestos y trámites, Mantenimiento
- **Categorías ambas**: Préstamos y devoluciones, Otros
- **Formas de pago**: BBVA crédito (día 22), Mercado Pago (día 16), Débito BBVA, Efectivo

---

## 6. Fase 2 — capa `core`

Misma organización que `apps/web/src/app/core/` en kaee.

### `supabase.service.ts`

Un único cliente para toda la app. Nadie más llama a `createClient`:

```ts
import { Service } from '@angular/core';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { environment } from '../../environments/environment';

@Service()
export class SupabaseService {
  readonly client: SupabaseClient = createClient(
    environment.supabaseUrl,
    environment.supabaseAnonKey,
  );
}
```

> Ojo con el decorador: en Angular 22 los servicios de `apps/web` en kaee usan **`@Service()`**, no `@Injectable()`. Las librerías de `packages/` todavía usan `@Injectable({ providedIn: 'root' })`. Sigue esa misma división.

### `auth.service.ts`

Envuelve `supabase.auth` con signals para que guards y pantallas reaccionen a la sesión sin tocar el cliente. Piezas que kaee resolvió y conviene copiar:

- `autenticado()` — computed sobre la sesión.
- `listo` — promesa que resuelve cuando ya se leyó la sesión guardada del navegador. **Sin esto los guards redirigen de más en el primer render.**
- `mensajeErrorAuth(error)` — mapa de errores de Supabase a español (`Invalid login credentials` → `Correo o contraseña incorrectos.`).

### `auth.guard.ts`

```ts
export const authGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  await auth.listo;
  if (auth.autenticado()) return true;
  return router.parseUrl('/login');
};

// Inverso, para /login y /registro: si ya hay sesión, no tiene caso mostrarlos.
export const soloInvitadoGuard: CanActivateFn = async () => { /* ... */ };
```

### `app.config.ts`

```ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(appRoutes, withComponentInputBinding()),
    provideIonicAngular(),
  ],
};
```

---

## 7. Fase 3 — features y rutas

```
apps/web/src/app/features/
├── auth/
│   ├── login/
│   ├── registro/
│   ├── recuperar-password/
│   └── restablecer-password/
├── resumen/          # el Home
├── entradas/
├── salidas/
└── catalogo/
```

`app.routes.ts`:

```ts
export const appRoutes: Route[] = [
  { path: 'login', component: Login, canActivate: [soloInvitadoGuard] },
  { path: 'registro', component: Registro, canActivate: [soloInvitadoGuard] },
  { path: 'recuperar-password', component: RecuperarPassword, canActivate: [soloInvitadoGuard] },
  // Sin guard de invitado: llega desde el enlace del correo, que ya trae sesión temporal.
  { path: 'restablecer-password', component: RestablecerPassword },

  { path: '', component: Resumen, canActivate: [authGuard] },
  { path: 'entradas', component: Entradas, canActivate: [authGuard] },
  { path: 'salidas', component: Salidas, canActivate: [authGuard] },
  { path: 'catalogo', component: Catalogo, canActivate: [authGuard] },
];
```

Cuando aparezcan roles (dueño vs. capturista), se agregan guards de rol como los `propietarioGuard` / `recepcionOAdminGuard` de kaee.

---

## 8. Convenciones de kaee que hay que respetar

Esto es lo que hace que el código se vea del mismo repo:

1. **Nombres de archivo sin `.component`.** Es `entradas.ts`, `entradas.html`, `entradas.scss` — no `entradas.component.ts`.
2. **Clases sin sufijo `Component`.** `export class Entradas`, no `EntradasComponent`.
3. **Standalone siempre.** Nada de `NgModule`.
4. **Ionic standalone.** Se importan los componentes uno por uno desde `@ionic/angular/standalone`:
   ```ts
   import { IonContent, IonIcon } from '@ionic/angular/standalone';
   import { addIcons } from 'ionicons';
   import { arrowBackOutline, searchOutline } from 'ionicons/icons';
   ```
   Los iconos se registran con `addIcons({ ... })` en el constructor del componente.
5. **Signals, no RxJS para estado local.** `signal()`, `computed()`, `resource()` e `inject()`. RxJS solo si algo lo exige.
6. **Tipos y constantes arriba del archivo**, antes de la clase (`type Vista = 'lista' | 'alta'`).
7. **Comentarios en español que explican el porqué, no el qué.** Los de kaee justifican decisiones ("security invoker: respeta las mismas policies RLS"). Copia ese tono.
8. **SCSS** como `inlineStyleLanguage`.
9. **Migraciones con timestamp**: `supabase/migrations/20260815120000_nombre_descriptivo.sql`.
10. **Alias `@org/*`** para todo lo que viva en `packages/`, declarados en `tsconfig.base.json`.

---

## 9. Orden de trabajo sugerido

| # | Entregable | Cómo sabes que quedó |
|---|---|---|
| 1 | Workspace Nx + app web + Ionic | `nx serve web` levanta y renderiza un `<ion-content>` |
| 2 | Proyecto Supabase + esquema + RLS | Consultar `movimientos` sin sesión devuelve 0 filas |
| 3 | `core/` completo + login | Entras, recargas y sigues dentro |
| 4 | Catálogo (CRUD) | Das de alta un proveedor y aparece en el selector de Salidas |
| 5 | Salidas | Registras una compra y sale en la tabla y en gasto por tarjeta |
| 6 | Entradas | Registras un ingreso con categoría de nómina |
| 7 | Resumen con la RPC | Los cuatro tiles y el desglose por categoría cuadran con las tablas |
| 8 | Estética del board | Verde neón, scanlines, esquinas en corchete, barra segmentada |
| 9 | Capacitor Android | `nx build web && npx cap sync && npx cap open android` |

De 4 a 6 antes que el 7: el resumen no se puede validar sin datos que resumir.

---

## 10. CI

Copia `.github/workflows/ci.yml` de kaee. Lo esencial:

```yaml
- uses: actions/setup-node@v5
  with:
    node-version: 24
    cache: 'npm'
- run: npm ci
- run: npx playwright install --with-deps
- run: npx nx format:check --base="remotes/origin/main"
- run: npx nx run-many -t lint test build typecheck e2e
```

Nx Cloud y `nx fix-ci` son opcionales; quítalos si no vas a conectar el workspace.

---

## 11. Qué NO copiar de kaee

- **El `README.md`**: es el del template de Nx y habla de una app `shop` que no existe. Escribe uno propio.
- **`packages/shop/*`**: sobras del preset (`feature-products`, `product-detail`, `shared-ui` de tienda). No las generes.
- **El modelo de inventario** (lotes, contenedores, documentos, pedidos): es de otro dominio.
- **Las credenciales de `environment.ts`**: apuntan al Supabase de kaee.
- **`proxy.conf.json` y `dependsOn: ["api:serve"]`**: solo aplican si generas `apps/api`.
