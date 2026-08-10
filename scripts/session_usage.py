#!/usr/bin/env python3
"""Lee el transcript local de la sesión de Claude Code y genera un panel HTML
con el consumo de contexto, tokens, coste equivalente y ritmo de la sesión.

Uso:
    python3 scripts/session_usage.py [--out RUTA.html]

Sin argumentos toma la sesión indicada por $CLAUDE_CODE_SESSION_ID (o la más
reciente del proyecto actual) y escribe el panel junto al script.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Ventana de contexto y precios de lista por millón de tokens.
MODEL_SPECS = {
    "claude-opus-5": {"window": 1_000_000, "input": 5.00, "output": 25.00},
    "claude-opus-4-8": {"window": 1_000_000, "input": 5.00, "output": 25.00},
    "claude-sonnet-5": {"window": 1_000_000, "input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"window": 200_000, "input": 1.00, "output": 5.00},
}
DEFAULT_SPEC = MODEL_SPECS["claude-opus-5"]

# Multiplicadores de caché sobre el precio de entrada.
CACHE_WRITE_5M = 1.25
CACHE_WRITE_1H = 2.00
CACHE_READ = 0.10


def find_transcript() -> Path:
    """Localiza el .jsonl de la sesión en curso."""
    cwd_key = "-" + os.getcwd().strip("/").replace("/", "-")
    project_dir = Path.home() / ".claude" / "projects" / cwd_key
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    candidate = project_dir / f"{session_id}.jsonl"
    if session_id and candidate.exists():
        return candidate
    matches = sorted(glob.glob(str(project_dir / "*.jsonl")), key=os.path.getmtime)
    if not matches:
        raise SystemExit(f"No se encontró ningún transcript en {project_dir}")
    return Path(matches[-1])


def parse(transcript: Path) -> dict:
    """Agrupa el transcript por requestId: una petición al modelo por fila."""
    requests: dict[str, dict] = {}
    order: list[str] = []
    first_ts = last_ts = None
    meta: dict[str, str] = {}
    prompts = 0

    for line in transcript.read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        ts = entry.get("timestamp")
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        if entry.get("type") == "user" and not entry.get("isSidechain"):
            content = entry.get("message", {}).get("content")
            if isinstance(content, str) or entry.get("type") == "last-prompt":
                prompts += 1
        if entry.get("type") != "assistant":
            continue

        rid = entry.get("requestId")
        if not rid or rid in requests:
            continue  # el transcript repite la misma petición por cada bloque

        usage = entry.get("message", {}).get("usage", {})
        creation = usage.get("cache_creation", {})
        requests[rid] = {
            "ts": entry.get("timestamp"),
            "input": usage.get("input_tokens", 0),
            "cache_write": usage.get("cache_creation_input_tokens", 0),
            "cache_write_1h": creation.get("ephemeral_1h_input_tokens", 0),
            "cache_write_5m": creation.get("ephemeral_5m_input_tokens", 0),
            "cache_read": usage.get("cache_read_input_tokens", 0),
            "output": usage.get("output_tokens", 0),
        }
        order.append(rid)
        meta = {
            "model": entry.get("message", {}).get("model", "?"),
            "effort": entry.get("effort", "?"),
            "version": entry.get("version", "?"),
            "entrypoint": entry.get("entrypoint", "?"),
            "branch": entry.get("gitBranch", "?"),
            "session": entry.get("sessionId", "?"),
        }

    rows = []
    for rid in order:
        r = requests[rid]
        r["context"] = r["input"] + r["cache_write"] + r["cache_read"]
        r["id"] = rid[-8:]
        rows.append(r)

    spec = MODEL_SPECS.get(meta.get("model", ""), DEFAULT_SPEC)
    totals = {
        k: sum(r[k] for r in rows)
        for k in ("input", "cache_write", "cache_write_1h", "cache_write_5m", "cache_read", "output")
    }
    context_now = rows[-1]["context"] if rows else 0

    per_mtok = lambda n, mult=1.0: n / 1_000_000 * spec["input"] * mult
    cost = {
        "input": per_mtok(totals["input"]),
        "cache_write": per_mtok(totals["cache_write_5m"], CACHE_WRITE_5M)
        + per_mtok(totals["cache_write_1h"], CACHE_WRITE_1H),
        "cache_read": per_mtok(totals["cache_read"], CACHE_READ),
        "output": totals["output"] / 1_000_000 * spec["output"],
    }
    cost["total"] = sum(cost.values())
    # Lo que costaría sin caché: todo el prefijo a precio de entrada completo.
    cost["sin_cache"] = (
        per_mtok(totals["input"] + totals["cache_write"] + totals["cache_read"])
        + cost["output"]
    )

    # Ritmo: cuánto crece el contexto por petición y cuántas quedan hasta autocompactar.
    threshold_pct = int(os.environ.get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "80"))
    threshold = spec["window"] * threshold_pct / 100
    growth = [rows[i]["context"] - rows[i - 1]["context"] for i in range(1, len(rows))]
    avg_growth = sum(growth) / len(growth) if growth else context_now
    headroom = max(threshold - context_now, 0)
    turns_left = int(headroom / avg_growth) if avg_growth > 0 else None

    return {
        "meta": meta,
        "rows": rows,
        "totals": totals,
        "cost": cost,
        "spec": spec,
        "context_now": context_now,
        "threshold": threshold,
        "threshold_pct": threshold_pct,
        "headroom": headroom,
        "avg_growth": avg_growth,
        "turns_left": turns_left,
        "prompts": prompts,
        "started": first_ts,
        "updated": last_ts,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "transcript": str(transcript),
    }


def fmt(n: float) -> str:
    return f"{round(n):,}".replace(",", " ")


def render(d: dict) -> str:
    rows = d["rows"]
    spec = d["spec"]
    window = spec["window"]
    pct = d["context_now"] / window * 100
    max_ctx = max((r["context"] for r in rows), default=1)

    elapsed = 0
    if d["started"] and d["updated"]:
        t0 = datetime.fromisoformat(d["started"].replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(d["updated"].replace("Z", "+00:00"))
        elapsed = (t1 - t0).total_seconds()

    def hhmm(secs: float) -> str:
        secs = int(secs)
        return f"{secs // 3600:d}:{secs % 3600 // 60:02d}:{secs % 60:02d}"

    ledger = "\n".join(
        f"""          <tr>
            <td class="mono dim">{r['id']}</td>
            <td class="mono">{r['ts'][11:19]}</td>
            <td class="num">{fmt(r['input'])}</td>
            <td class="num">{fmt(r['cache_write'])}</td>
            <td class="num dim">{fmt(r['cache_read'])}</td>
            <td class="num">{fmt(r['output'])}</td>
            <td class="num strong">{fmt(r['context'])}</td>
          </tr>"""
        for r in rows
    )

    bars = "\n".join(
        f"""          <div class="bar" style="--h:{r['context'] / max_ctx * 100:.1f}%">
            <span class="bar-fill"></span>
            <span class="bar-label mono">{r['id'][:4]}</span>
          </div>"""
        for r in rows
    )

    state = "ok" if pct < 50 else ("warn" if pct < d["threshold_pct"] else "crit")
    turns = d["turns_left"]
    turns_txt = f"~{turns}" if turns is not None else "—"

    return f"""<title>Consumo de la sesión · Claude Code</title>
<style>
  :root {{
    --bg: #EDF0EF;
    --surface: #FFFFFF;
    --surface-2: #F5F7F6;
    --line: #D5DCD9;
    --line-soft: #E4EAE8;
    --text: #101D1A;
    --muted: #5C6E69;
    --accent: #12766A;
    --accent-soft: #12766A1F;
    --ok: #2E7D4F;
    --warn: #B0740A;
    --crit: #AE3128;
    --shadow: 0 1px 2px #0f231f0f, 0 8px 24px -12px #0f231f24;
    --mono: ui-monospace, "SF Mono", "Cascadia Mono", "Roboto Mono", Menlo, Consolas, monospace;
    --sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #0B1412;
      --surface: #121D1A;
      --surface-2: #17231F;
      --line: #24332E;
      --line-soft: #1C2A26;
      --text: #E4EDE9;
      --muted: #90A49E;
      --accent: #4FBFA9;
      --accent-soft: #4FBFA924;
      --ok: #57B67E;
      --warn: #D9A03C;
      --crit: #E0705F;
      --shadow: 0 1px 2px #0006, 0 10px 30px -14px #000a;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #0B1412;
    --surface: #121D1A;
    --surface-2: #17231F;
    --line: #24332E;
    --line-soft: #1C2A26;
    --text: #E4EDE9;
    --muted: #90A49E;
    --accent: #4FBFA9;
    --accent-soft: #4FBFA924;
    --ok: #57B67E;
    --warn: #D9A03C;
    --crit: #E0705F;
    --shadow: 0 1px 2px #0006, 0 10px 30px -14px #000a;
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    font-size: 15px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{
    max-width: 940px;
    margin: 0 auto;
    padding: 40px 20px 72px;
    display: flex;
    flex-direction: column;
    gap: 28px;
  }}
  .mono {{ font-family: var(--mono); font-variant-numeric: tabular-nums; }}
  .dim {{ color: var(--muted); }}
  .eyebrow {{
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: var(--muted);
    margin: 0;
  }}

  header h1 {{
    font-family: var(--mono);
    font-size: clamp(26px, 5vw, 36px);
    font-weight: 600;
    letter-spacing: -.02em;
    margin: 6px 0 12px;
    text-wrap: balance;
  }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{
    font-family: var(--mono);
    font-size: 11.5px;
    padding: 3px 9px;
    border: 1px solid var(--line);
    border-radius: 2px;
    background: var(--surface);
    color: var(--muted);
  }}
  .chip b {{ color: var(--text); font-weight: 600; }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 4px;
    box-shadow: var(--shadow);
    padding: 22px;
  }}
  .card > h2 {{
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: var(--muted);
    font-weight: 600;
    margin: 0 0 16px;
  }}

  /* ---- Medidor principal ---- */
  .gauge-top {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
  .gauge-value {{ font-family: var(--mono); font-size: clamp(38px, 8vw, 56px); font-weight: 600; letter-spacing: -.03em; line-height: 1; }}
  .gauge-value small {{ font-size: .38em; font-weight: 500; color: var(--muted); letter-spacing: 0; }}
  .gauge-side {{ text-align: right; font-family: var(--mono); font-size: 13px; color: var(--muted); }}
  .gauge-side b {{ display: block; font-size: 19px; color: var(--text); font-weight: 600; }}

  .meter {{
    position: relative;
    height: 30px;
    margin: 20px 0 10px;
    background: var(--surface-2);
    border: 1px solid var(--line-soft);
    border-radius: 2px;
    overflow: hidden;
  }}
  .meter-fill {{
    position: absolute; inset: 0 auto 0 0;
    background: var(--accent);
    border-right: 1px solid var(--surface);
  }}
  .meter[data-state="warn"] .meter-fill {{ background: var(--warn); }}
  .meter[data-state="crit"] .meter-fill {{ background: var(--crit); }}
  .meter-mark {{
    position: absolute; top: 0; bottom: 0; width: 2px;
    background: var(--text); opacity: .55;
  }}
  .meter-scale {{
    display: flex; justify-content: space-between;
    font-family: var(--mono); font-size: 11px; color: var(--muted);
  }}
  .legend {{ display: flex; gap: 18px; flex-wrap: wrap; margin-top: 14px; font-size: 13px; color: var(--muted); }}
  .legend span::before {{
    content: ""; display: inline-block; width: 9px; height: 9px;
    margin-right: 7px; border-radius: 1px; vertical-align: baseline;
  }}
  .legend .k-used::before {{ background: var(--accent); }}
  .legend .k-mark::before {{ background: var(--text); opacity: .55; }}
  .legend .k-free::before {{ background: var(--surface-2); border: 1px solid var(--line); }}

  /* ---- Rejilla de indicadores ---- */
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 4px; overflow: hidden; }}
  .stat {{ background: var(--surface); padding: 18px 20px; display: flex; flex-direction: column; gap: 3px; }}
  .stat dt {{ font-family: var(--mono); font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); }}
  .stat dd {{ margin: 0; font-family: var(--mono); font-size: 25px; font-weight: 600; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }}
  .stat p {{ margin: 0; font-size: 12.5px; color: var(--muted); }}
  .stat dd.pos {{ color: var(--ok); }}

  /* ---- Gráfico de crecimiento ---- */
  .chart {{ display: flex; align-items: flex-end; gap: 6px; height: 150px; padding-top: 8px; }}
  .bar {{ flex: 1; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 6px; height: 100%; }}
  .bar-fill {{ width: 100%; height: var(--h); background: var(--accent-soft); border-top: 2px solid var(--accent); border-radius: 1px 1px 0 0; }}
  .bar:last-child .bar-fill {{ background: var(--accent); border-top-color: var(--accent); }}
  .bar-label {{ font-size: 10px; color: var(--muted); }}

  /* ---- Tabla ---- */
  .scroll {{ overflow-x: auto; margin: 0 -22px; padding: 0 22px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--line-soft); white-space: nowrap; }}
  th {{
    font-family: var(--mono); font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase;
    color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--line);
  }}
  td.num, th.num {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; }}
  td.strong {{ font-weight: 600; }}
  tbody tr:last-child td {{ border-bottom: 0; }}
  tfoot td {{ border-top: 1px solid var(--line); border-bottom: 0; font-weight: 600; font-family: var(--mono); }}

  /* ---- Coste ---- */
  .cost {{ display: grid; grid-template-columns: 1fr auto; gap: 8px 20px; font-size: 14px; }}
  .cost dt {{ color: var(--muted); }}
  .cost dd {{ margin: 0; font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: right; }}
  .cost .rule {{ grid-column: 1 / -1; height: 1px; background: var(--line); margin: 6px 0; }}
  .cost .total {{ font-weight: 600; color: var(--text); }}
  .saved {{ margin-top: 16px; padding: 12px 14px; background: var(--accent-soft); border-left: 2px solid var(--accent); font-size: 13.5px; }}

  /* ---- Nota ---- */
  .note {{ border-color: var(--line); background: var(--surface-2); }}
  .note p {{ margin: 0 0 12px; max-width: 66ch; }}
  .note p:last-child {{ margin-bottom: 0; }}
  code {{ font-family: var(--mono); font-size: .9em; background: var(--surface); border: 1px solid var(--line); border-radius: 2px; padding: 1px 5px; }}

  footer {{ font-size: 12.5px; color: var(--muted); font-family: var(--mono); }}
  @media (max-width: 560px) {{
    .wrap {{ padding: 28px 14px 56px; }}
    .card {{ padding: 18px 16px; }}
    .scroll {{ margin: 0 -16px; padding: 0 16px; }}
  }}
</style>

<div class="wrap">
  <header>
    <p class="eyebrow">Panel de sesión · Claude Code</p>
    <h1>Cuánto te queda en esta sesión</h1>
    <div class="chips">
      <span class="chip">modelo <b>{d['meta']['model']}</b></span>
      <span class="chip">esfuerzo <b>{d['meta']['effort']}</b></span>
      <span class="chip">CLI <b>v{d['meta']['version']}</b></span>
      <span class="chip">rama <b>{d['meta']['branch']}</b></span>
      <span class="chip">sesión <b>{d['meta']['session'][:8]}</b></span>
    </div>
  </header>

  <section class="card">
    <h2>Ventana de contexto</h2>
    <div class="gauge-top">
      <div class="gauge-value">{pct:.1f}<small>%</small></div>
      <div class="gauge-side">
        <b>{fmt(d['headroom'])}</b>
        tokens libres antes de autocompactar
      </div>
    </div>
    <div class="meter" data-state="{state}">
      <span class="meter-fill" style="width:{min(pct, 100):.2f}%"></span>
      <span class="meter-mark" style="left:{d['threshold_pct']}%"></span>
    </div>
    <div class="meter-scale">
      <span>0</span>
      <span>{fmt(d['context_now'])} de {fmt(window)} tokens</span>
      <span>{fmt(window)}</span>
    </div>
    <div class="legend">
      <span class="k-used">Contexto en uso</span>
      <span class="k-mark">Autocompactación · {d['threshold_pct']}% ({fmt(d['threshold'])})</span>
      <span class="k-free">Disponible</span>
    </div>
  </section>

  <dl class="stats">
    <div class="stat">
      <dt>Turnos restantes</dt>
      <dd>{turns_txt}</dd>
      <p>Al ritmo actual de {fmt(d['avg_growth'])} tokens por petición</p>
    </div>
    <div class="stat">
      <dt>Tiempo activo</dt>
      <dd id="clock">{hhmm(elapsed)}</dd>
      <p>Desde las {d['started'][11:16]} UTC</p>
    </div>
    <div class="stat">
      <dt>Peticiones al modelo</dt>
      <dd>{len(rows)}</dd>
      <p>{fmt(d['totals']['output'])} tokens generados</p>
    </div>
    <div class="stat">
      <dt>Coste equivalente</dt>
      <dd>${d['cost']['total']:.3f}</dd>
      <p>Precio de lista; en plan de suscripción no se factura</p>
    </div>
  </dl>

  <section class="card">
    <h2>Crecimiento del contexto por petición</h2>
    <div class="chart">
{bars}
    </div>
    <p class="dim" style="margin:14px 0 0;font-size:13px">
      Cada barra es el contexto total enviado en esa petición. El salto grande corresponde
      a la carga de una skill extensa: el contexto no baja hasta que se autocompacta.
    </p>
  </section>

  <section class="card">
    <h2>Detalle por petición</h2>
    <div class="scroll">
      <table>
        <thead>
          <tr>
            <th>Petición</th>
            <th>Hora UTC</th>
            <th class="num">Entrada</th>
            <th class="num">Caché escrita</th>
            <th class="num">Caché leída</th>
            <th class="num">Salida</th>
            <th class="num">Contexto</th>
          </tr>
        </thead>
        <tbody>
{ledger}
        </tbody>
        <tfoot>
          <tr>
            <td colspan="2">Total</td>
            <td class="num">{fmt(d['totals']['input'])}</td>
            <td class="num">{fmt(d['totals']['cache_write'])}</td>
            <td class="num">{fmt(d['totals']['cache_read'])}</td>
            <td class="num">{fmt(d['totals']['output'])}</td>
            <td class="num">{fmt(d['context_now'])}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  </section>

  <section class="card">
    <h2>Coste equivalente a precio de lista</h2>
    <dl class="cost">
      <dt>Entrada sin cachear · {fmt(d['totals']['input'])} tok</dt>
      <dd>${d['cost']['input']:.4f}</dd>
      <dt>Escritura de caché · {fmt(d['totals']['cache_write'])} tok</dt>
      <dd>${d['cost']['cache_write']:.4f}</dd>
      <dt>Lectura de caché · {fmt(d['totals']['cache_read'])} tok</dt>
      <dd>${d['cost']['cache_read']:.4f}</dd>
      <dt>Salida · {fmt(d['totals']['output'])} tok</dt>
      <dd>${d['cost']['output']:.4f}</dd>
      <div class="rule"></div>
      <dt class="total">Total de la sesión</dt>
      <dd class="total">${d['cost']['total']:.4f}</dd>
    </dl>
    <p class="saved">
      Sin caché de prompts, este mismo trabajo costaría
      <b>${d['cost']['sin_cache']:.4f}</b> — la caché ahorra
      <b>${max(d['cost']['sin_cache'] - d['cost']['total'], 0):.4f}</b>
      ({max((1 - d['cost']['total'] / d['cost']['sin_cache']) * 100, 0):.0f}%).
    </p>
  </section>

  <section class="card note">
    <h2>Lo que este panel no puede ver</h2>
    <p>
      Todo lo de arriba sale del transcript local de esta sesión, así que es exacto.
      Pero <b>la cuota de tu plan es otra cosa</b>: el límite de la ventana de 5 horas y el
      semanal viven en el servidor y no quedan registrados en el transcript. Este panel
      no puede leerlos.
    </p>
    <p>
      Para ver cuánto te queda de la cuota del plan, usa <code>/usage</code> en Claude Code,
      o consulta el apartado de uso en claude.ai. Lo que sí te dice este panel es lo que
      limita <em>esta</em> conversación en concreto: cuánto contexto has gastado y cuántos
      turnos más aguanta antes de que se autocompacte el historial.
    </p>
    <p>
      Tampoco hay un límite de tiempo por sesión: el contenedor se recicla tras un rato de
      inactividad, no por reloj. Por eso el cronómetro mide actividad, no una cuenta atrás.
    </p>
  </section>

  <footer>
    Instantánea del {d['generated'][:16].replace('T', ' ')} UTC · fuente: {d['transcript']}<br>
    Regenerar con <code>python3 scripts/session_usage.py</code>
  </footer>
</div>

<script>
  (function () {{
    var el = document.getElementById("clock");
    if (!el) return;
    var start = new Date("{d['started']}").getTime();
    function tick() {{
      var s = Math.max(0, Math.floor((Date.now() - start) / 1000));
      var p = function (n) {{ return String(n).padStart(2, "0"); }};
      el.textContent = Math.floor(s / 3600) + ":" + p(Math.floor(s / 60) % 60) + ":" + p(s % 60);
    }}
    tick();
    setInterval(tick, 1000);
  }})();
</script>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("session-usage.html")))
    ap.add_argument("--transcript", default=None)
    args = ap.parse_args()

    transcript = Path(args.transcript) if args.transcript else find_transcript()
    data = parse(transcript)
    Path(args.out).write_text(render(data))
    print(f"{args.out}  ·  {len(data['rows'])} peticiones  ·  contexto {fmt(data['context_now'])}")


if __name__ == "__main__":
    main()
