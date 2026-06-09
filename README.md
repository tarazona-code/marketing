# Diagnóstico Radical del Funnel — Dashboard

Dashboard interactivo (Streamlit) que diagnostica la fuga de capital en el funnel
de marketing: embudo Lead→MQL→SQL, costo real por SQL y motor de decisiones.

## Cómo desplegarlo a una URL pública (gratis, ~3 min)

1. Crea un repositorio en GitHub y sube estos 3 archivos:
   - `app.py`
   - `requirements.txt`
   - `datos_atribucion_crudos.xlsx`
2. Entra a https://share.streamlit.io e inicia sesión con tu cuenta de GitHub.
3. Clic en "Create app" → elige tu repo → archivo principal: `app.py` → "Deploy".
4. En ~2 minutos tendrás tu URL pública (ej: https://tu-app.streamlit.app).

## Correr en local
```
pip install -r requirements.txt
streamlit run app.py
```

## Reglas analíticas aplicadas
1. Costos $0.00 = tráfico orgánico/automatizado real (no dato faltante); pagado y orgánico separados.
2. Duplicados ocultos por id_pixel_facebook: marcados, cuantificados y con vista deduplicada.
3. Embudo reconstruido de forma acumulada; el snapshot revela el quiebre MQL<SQL.
4. Febrero 2026 (fuera del rango mar-may) excluido de KPIs por defecto.
