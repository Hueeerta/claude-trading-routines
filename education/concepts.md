# Conceptos

Lista secuencial. Las rutinas toman uno por día (rotación por fecha) y lo ligan a lo que pasó.
Formato: cada concepto es un `### Título` seguido de 1-2 frases.

### Riesgo por operación
Cuánto pierdes si salta el stop, como % del equity. Aquí es 2%. Define el tamaño de la posición, no al revés.

### Position sizing
Tamaño = (equity × riesgo%) / distancia al stop. Stops más lejanos => posiciones más chicas para arriesgar lo mismo.

### Stop loss
Precio donde admites que la idea falló y sales. Va puesto en el exchange (OCO), no en tu cabeza.

### Riesgo de ruina
Probabilidad de quebrar la cuenta. Crece brutal con el riesgo por trade: a 10%/trade, 7 pérdidas seguidas te liquidan.

### Expectancy
Ganancia promedio por trade = (win% × ganancia media) − (loss% × pérdida media). Si es positiva, el sistema tiene ventaja.

### Profit factor
Ganancia bruta / pérdida bruta. >1 es rentable; >1.5 es bueno; <1 pierde dinero.

### Win rate
% de trades ganadores. Engañoso solo: un 40% de aciertos con ganadores grandes puede ser muy rentable.

### Drawdown
Caída desde el máximo de equity. El máximo histórico mide cuánto dolor aguantó la estrategia.

### Ratio riesgo/beneficio
Cuánto buscas ganar por cada unidad arriesgada. Con R:R 2:1 puedes ser rentable acertando solo 40%.

### Interés compuesto
Reinvertir ganancias hace crecer el capital exponencialmente. Solo funciona si no tienes drawdowns que lo destruyan.

### Tendencia
Secuencia de máximos y mínimos crecientes (alcista) o decrecientes (bajista). Operar a favor de la tendencia mayor mejora las probabilidades.

### EMA (media exponencial)
Promedio que pondera más los precios recientes. Cruces y pendiente se usan como señal de tendencia.

### RSI
Oscilador 0-100 de fuerza relativa. >70 sobrecompra, <30 sobreventa, pero en tendencia fuerte puede quedarse extremo mucho tiempo.

### ATR
Average True Range: volatilidad media. Se usa para poner stops proporcionales al ruido del activo.

### Bandas de Bollinger
Media móvil ± desviaciones estándar. Mide cuán lejos del promedio está el precio.

### Canal de Donchian
Máximo y mínimo de N velas. Rupturas del canal señalan breakouts.

### Soporte y resistencia
Zonas donde el precio históricamente reaccionó. Útiles para ubicar stops y targets.

### Volumen
Cantidad negociada. Una ruptura con volumen alto es más confiable que una sin volumen.

### Régimen de mercado
Tendencia, rango o alta volatilidad. Cada estrategia funciona en un régimen; ninguna en todos.

### Reversión a la media
En rango, los extremos tienden a volver al promedio. Base de las estrategias de mean-reversion.

### Breakout
Ruptura de un nivel clave. Puede ser real (con seguimiento) o falsa (fakeout); por eso se confirma con volumen.

### Slippage
Diferencia entre el precio esperado y el ejecutado. En backtest hay que restarlo para no engañarse.

### Comisiones
Costo por operar. Pequeñas por trade, pero erosionan mucho a alta frecuencia.

### Overfitting
Ajustar parámetros tanto al pasado que dejan de funcionar a futuro. Por eso se valida fuera de muestra (out-of-sample).

### Backtest honesto
Incluye comisiones, slippage y no usa datos del futuro. Un backtest optimista miente.

### Out-of-sample
Reservar datos que el sistema no vio al optimizar, para probar si la ventaja es real.

### Psicología: FOMO
Miedo a quedarse fuera. Empuja a entrar tarde y sin plan. El sistema automático lo neutraliza.

### Psicología: revenge trading
Operar para "recuperar" una pérdida. Suele agrandar el pozo. La regla manda, no la emoción.

### Funding rate
Tasa de perpetuos. Muy positiva = mercado apalancado en largo (riesgo de liquidaciones en cadena).

### Fear & Greed
Índice de sentimiento 0-100. Extremos suelen coincidir con giros, no como señal única sino como contexto.
