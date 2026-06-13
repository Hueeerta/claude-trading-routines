# Claude TradeBot

Sistema de **paper trading** de cripto (Binance Spot Testnet) operado por rutinas remotas de Claude. Swing trading en 4H/Diario. Objetivo: validar una estrategia con ventaja estadística y aprender, antes de arriesgar capital real.

## Expectativas realistas (leer)

- La mayoría de los traders retail pierde dinero. El objetivo de los primeros **3-6 meses es aprender y validar**, no ganar.
- La estrategia es **determinista** (reglas en Python, reproducibles y backtesteables). Claude **no inventa ni veta** señales: ejecuta las reglas, supervisa y registra una lectura paralela no vinculante.
- **No se opera con dinero real** hasta cumplir: ≥8 semanas de paper, ≥30 trades, métricas positivas, y decisión explícita del usuario.
- Riesgo máximo **2% del equity por operación**. No negociable sin revisión conjunta.

## Cómo funciona

```
Rutina remota (cloud) → briefing.py (contexto) → datos+feeds → estrategia determinista
   → riesgo (2%) → orden en testnet (con stop OCO) → ledger JSONL → commit/push → Telegram
```

- **Datos** de mercado: API pública de producción de Binance (reales).
- **Órdenes**: solo Binance Spot Testnet.
- **Fuente de verdad**: ledger JSONL versionado en Git (la testnet se resetea ~mensual). SQLite se reconstruye desde el ledger para análisis/dashboard.

## Estructura

- `tradebot/` — motor: datos, feeds, indicadores, estrategias, riesgo, executor, ledger, briefing, notify.
- `scripts/` — CLIs que invocan las rutinas (salida JSON compacta).
- `config/settings.yaml` — pares, timeframe, riesgo, parámetros.
- `ledger/` — JSONL append-only (trades, equity, journal). **Versionado.**
- `education/concepts.md` — conceptos para reforzar aprendizaje.

## Setup local

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar credenciales
```

## Comandos

```bash
python scripts/run_cycle.py --dry-run        # ciclo sin ejecutar órdenes
python scripts/backtest.py --strategy trend_ema
python scripts/report_daily.py
python scripts/report_weekly.py
python scripts/rebuild_sqlite.py             # reconstruye db/trades.db desde el ledger
```

## Fases

0. Infraestructura (actual) · 1. Encontrar estrategia (backtest) · 2. Paper ≥8 semanas · 3. Evaluar y decidir capital real.
