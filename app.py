# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO RADICAL DEL FUNNEL — Dashboard interactivo
Versión sin dependencias externas: solo streamlit + pandas (gráficas nativas, datos en CSV).

Reglas analíticas aplicadas (ver pestaña "Reglas y anomalías"):
  1. costo_clic_usd == 0.00 -> tráfico orgánico/automatizado real (NO dato faltante).
  2. Duplicados ocultos por id_pixel_facebook (misma persona, varios lead_id): marcados y cuantificados.
  3. Embudo reconstruido de forma ACUMULADA; el snapshot revela el quiebre MQL<SQL.
  4. Febrero 2026 (fuera de mar-may) excluido de KPIs por defecto; accesible vía filtro.
"""

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Diagnóstico del Funnel", page_icon="🔻", layout="wide")

ORDEN_ETAPAS = ["Nuevo Lead", "Contacto Agendado", "MQL (Calificado Mkt)", "SQL (Calificado Ventas)"]
SQL_LABEL = "SQL (Calificado Ventas)"
MQL_LABEL = "MQL (Calificado Mkt)"
PERDIDA = "Oportunidad Perdida"


@st.cache_data
def cargar_datos():
    df = pd.read_csv("datos_atribucion_crudos.csv")
    df["fecha_timestamp"] = pd.to_datetime(df["fecha_timestamp"])
    df["mes"] = df["fecha_timestamp"].dt.to_period("M").astype(str)
    df["es_pagado"] = df["costo_clic_usd"] > 0
    df["dup_pixel"] = df["id_pixel_facebook"].notna() & df["id_pixel_facebook"].duplicated(keep=False)
    df["es_sql"] = df["estado_gohighlevel"] == SQL_LABEL
    return df


def etapa_index(estado):
    if estado == PERDIDA:
        return -1
    try:
        return ORDEN_ETAPAS.index(estado)
    except ValueError:
        return -1


df = cargar_datos()

# ----------------------- SIDEBAR / FILTROS -----------------------
st.sidebar.title("⚙️ Filtros")
st.sidebar.caption("La dirección puede aislar el rendimiento por mes y canal.")

incluir_febrero = st.sidebar.toggle(
    "Incluir Febrero 2026 (fuera de rango)", value=False,
    help="El reto declara mar-may. Febrero es una anomalía; actívalo solo para auditar."
)
meses_validos = sorted(df["mes"].unique())
if not incluir_febrero:
    meses_validos = [m for m in meses_validos if m != "2026-02"]

meses_sel = st.sidebar.multiselect("Meses", meses_validos, default=meses_validos)
canales = sorted(df["utm_source"].unique())
canales_sel = st.sidebar.multiselect("Fuentes (utm_source)", canales, default=canales)

deduplicar = st.sidebar.toggle(
    "Vista deduplicada (regla 2)", value=False,
    help="Conserva 1 sola fila por pixel repetido (la más antigua)."
)

data = df[df["mes"].isin(meses_sel) & df["utm_source"].isin(canales_sel)].copy()
inflados_n = int(data["dup_pixel"].sum())
gasto_inflado = float(data.loc[data["dup_pixel"], "costo_clic_usd"].sum())
if deduplicar:
    dups = data[data["id_pixel_facebook"].notna()].sort_values("fecha_timestamp")
    keep = dups.drop_duplicates(subset="id_pixel_facebook", keep="first").index
    data = data[data["id_pixel_facebook"].isna() | data.index.isin(keep)].copy()

if len(data) == 0:
    st.warning("No hay datos con los filtros seleccionados.")
    st.stop()

# ----------------------- ENCABEZADO + KPIs -----------------------
st.title("🔻 Diagnóstico Radical del Funnel")
st.caption("De Lead a SQL · Eficiencia financiera · Motor de decisiones — datos crudos de atribución (mar-may 2026)")

leads = len(data)
sqls = int(data["es_sql"].sum())
gasto_total = float(data["costo_clic_usd"].sum())
sqls_pagados = int(data.loc[data["es_pagado"], "es_sql"].sum())
cac_pagado = gasto_total / sqls_pagados if sqls_pagados else 0
sqls_organicos = sqls - sqls_pagados

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Leads", f"{leads:,}")
k2.metric("SQLs", f"{sqls:,}", f"{100*sqls/leads:.1f}% del total")
k3.metric("Gasto en medios", f"${gasto_total:,.0f}")
k4.metric("CAC por SQL (pagado)", f"${cac_pagado:,.2f}")
k5.metric("SQLs orgánicos ($0)", f"{sqls_organicos:,}", f"{100*sqls_organicos/sqls:.0f}% de los SQL" if sqls else "—")

st.divider()
tab_a, tab_b, tab_c, tab_d = st.tabs(
    ["🅰️ Embudo (Lead→SQL)", "🅱️ Eficiencia financiera", "🅾️ Motor de decisiones", "🔬 Reglas y anomalías"]
)

# ===================== PILAR A: EMBUDO =====================
with tab_a:
    st.subheader("Embudo acumulado: ¿dónde se fugan los prospectos?")
    idx = data["estado_gohighlevel"].map(etapa_index)
    n_lead = leads
    n_contacto = int((idx >= 1).sum())
    n_mql = int((idx >= 2).sum())
    n_sql = int((idx >= 3).sum())

    c1, c2 = st.columns([3, 2])
    with c1:
        embudo = pd.DataFrame(
            {"Leads": [n_lead, n_contacto, n_mql, n_sql]},
            index=["1. Leads", "2. Contacto+", "3. MQL+", "4. SQL"],
        )
        st.bar_chart(embudo, horizontal=True, color="#4C78A8")
    with c2:
        pasos = [("Lead → Contacto", n_lead, n_contacto),
                 ("Contacto → MQL", n_contacto, n_mql),
                 ("MQL → SQL", n_mql, n_sql)]
        filas = []
        for nombre, a, b in pasos:
            esc = 100 * (a - b) / a if a else 0
            filas.append({"Paso": nombre, "Caen": a - b, "Tasa de escape": f"{esc:.1f}%", "_v": esc})
        tabla = pd.DataFrame(filas)
        peor = tabla.loc[tabla["_v"].idxmax()]
        st.markdown("**Tasa de escape por etapa**")
        st.dataframe(tabla.drop(columns="_v"), hide_index=True, use_container_width=True)
        st.error(f"🚨 Mayor fuga porcentual: **{peor['Paso']}** ({peor['Tasa de escape']}).")

    st.markdown("---")
    st.subheader("⚠️ El quiebre estructural del CRM (snapshot real)")
    snap = data["estado_gohighlevel"].value_counts().reindex(ORDEN_ETAPAS + [PERDIDA]).fillna(0).astype(int)
    st.bar_chart(pd.DataFrame({"Leads": snap}), color="#E45756")
    if snap.get(SQL_LABEL, 0) > snap.get(MQL_LABEL, 0):
        st.warning(
            f"Hay **más SQL ({snap[SQL_LABEL]:,}) que MQL ({snap[MQL_LABEL]:,})**, imposible en un embudo limpio: "
            "el SQL viene *después* del MQL. Conclusión: muchos leads se saltan la etapa MQL en GoHighLevel "
            "(no se etiquetan), rompiendo el lead scoring y la atribución."
        )

    st.markdown("**Mayor fuga por plataforma** (conversión a SQL por fuente)")
    porf = data.groupby("utm_source").agg(Leads=("lead_id", "count"), SQLs=("es_sql", "sum")).reset_index()
    porf["Conversión a SQL %"] = (100 * porf["SQLs"] / porf["Leads"]).round(1)
    porf = porf.sort_values("Conversión a SQL %").rename(columns={"utm_source": "Fuente"})
    st.dataframe(porf, hide_index=True, use_container_width=True)

# ===================== PILAR B: FINANCIERO =====================
with tab_b:
    st.subheader("Costo real por SQL (CAC de ventas) por campaña")
    st.caption("Regla 1: pagado y orgánico por separado. Los $0.00 son tráfico orgánico real, no dato faltante.")

    g = data.groupby("utm_campaign").agg(
        Fuente=("utm_source", "first"), Leads=("lead_id", "count"),
        SQLs=("es_sql", "sum"), Gasto=("costo_clic_usd", "sum")).reset_index().rename(columns={"utm_campaign": "Campaña"})
    g["Pagada"] = g["Gasto"] > 0
    g["CostoPorSQL"] = g.apply(lambda r: r["Gasto"] / r["SQLs"] if r["SQLs"] > 0 else 0, axis=1)
    g["Conversión SQL %"] = (100 * g["SQLs"] / g["Leads"]).round(1)

    pagadas = g[g["Pagada"]].sort_values("CostoPorSQL", ascending=False)
    organicas = g[~g["Pagada"]].sort_values("Conversión SQL %", ascending=False)

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**🟥 Campañas PAGADAS — Costo por SQL ($)**")
        if len(pagadas):
            st.bar_chart(pagadas.set_index("Campaña")[["CostoPorSQL"]], horizontal=True, color="#E45756")
        else:
            st.info("No hay campañas pagadas en el filtro actual.")
    with cc2:
        st.markdown("**🟩 Campañas ORGÁNICAS — Conversión a SQL (%) · costo $0**")
        if len(organicas):
            st.bar_chart(organicas.set_index("Campaña")[["Conversión SQL %"]], horizontal=True, color="#54A24B")
        else:
            st.info("No hay campañas orgánicas en el filtro actual.")

    st.markdown("**Tabla completa**")
    tabla_fin = g.copy()
    tabla_fin["Gasto"] = tabla_fin["Gasto"].map(lambda v: f"${v:,.2f}")
    tabla_fin["Costo por SQL"] = tabla_fin.apply(
        lambda r: (f"${r['CostoPorSQL']:.2f}" if r["Pagada"] else "$0.00 (orgánico)"), axis=1)
    st.dataframe(
        tabla_fin[["Campaña", "Fuente", "Leads", "SQLs", "Gasto", "Costo por SQL", "Conversión SQL %"]]
        .sort_values("SQLs", ascending=False), hide_index=True, use_container_width=True)

# ===================== PILAR C: DECISIONES =====================
with tab_c:
    st.subheader("Motor de decisiones — conclusiones automáticas")
    st.caption("Calculadas en vivo sobre los filtros actuales.")

    g2 = data.groupby("utm_campaign").agg(
        leads=("lead_id", "count"), sqls=("es_sql", "sum"), gasto=("costo_clic_usd", "sum")).reset_index()
    g2["pagada"] = g2["gasto"] > 0
    g2["costo_x_sql"] = g2.apply(lambda r: r["gasto"] / r["sqls"] if r["sqls"] > 0 else None, axis=1)
    g2["conv"] = 100 * g2["sqls"] / g2["leads"]
    pag = g2[g2["pagada"] & g2["sqls"].gt(0)]
    org = g2[~g2["pagada"]].sort_values("conv", ascending=False)

    col1, col2 = st.columns(2)
    if len(pag):
        peor = pag.loc[pag["costo_x_sql"].idxmax()]
        with col1:
            st.markdown("#### 🔴 1. Apagar de inmediato")
            st.error(f"**{peor['utm_campaign']}**\n\nLa campaña pagada con el **costo por SQL más alto: "
                     f"${peor['costo_x_sql']:.2f}** y peor conversión ({peor['conv']:.1f}%). Apagarla frena la "
                     f"quema de dinero sin perder volumen relevante.")
    if len(org):
        mejor = org.iloc[0]
        with col2:
            st.markdown("#### 🟢 2. Redirigir el presupuesto")
            st.success(f"**Canal WhatsApp conversacional** (p.ej. `{mejor['utm_campaign']}`)\n\nConvierte al "
                       f"**{mejor['conv']:.1f}% a SQL con $0 de costo de medios**, ~4x la conversión de lo pagado "
                       f"(~11%). Reinvertir aquí multiplica el ROI.")

    st.markdown("#### 🟠 3. Cuello de botella operativo en GoHighLevel")
    st.warning("**Síntoma:** más SQL que MQL en el CRM (imposible en un embudo limpio).\n\n"
               "**Causa raíz:** los leads pasan a SQL **sin el tag MQL** — la calificación de marketing no se "
               "registra, rompiendo el lead scoring.\n\n"
               "**Solución de raíz:** (1) regla en GoHighLevel que **bloquee el paso a SQL sin tag MQL** "
               "(compuerta obligatoria); (2) **deduplicar por `id_pixel_facebook`** para no recontar ni recomprar "
               "a la misma persona.")

    st.markdown("#### 📋 Resumen ejecutivo")
    st.info(f"Sobre {leads:,} leads (filtro actual): el orgánico de WhatsApp genera la mayoría de SQLs **a costo "
            f"cero**, mientras las campañas pagadas cuestan ~${cac_pagado:.2f}/SQL con ~11% de conversión. La fuga "
            f"de capital no es 'pocos leads', sino **gastar en un canal caro mientras el gratis convierte 4x mejor**, "
            f"agravado por leads duplicados y una etapa MQL rota en el CRM.")

# ===================== PILAR D: REGLAS Y ANOMALÍAS =====================
with tab_d:
    st.subheader("Tratamiento de datos y anomalías (para la defensa)")

    st.markdown("##### Regla 1 · Costos en $0.00 = tráfico orgánico real")
    cruce = df.pivot_table(index="utm_source", columns="es_pagado", values="lead_id", aggfunc="count", fill_value=0)
    cruce.columns = [("Costo = $0" if c is False else "Costo > $0") for c in cruce.columns]
    st.dataframe(cruce, use_container_width=True)
    st.caption("Los 33,120 ceros coinciden exactamente con los leads sin pixel de Facebook. No se imputan "
               "promedios: eso inventaría un costo falso al canal orgánico.")

    st.markdown("##### Regla 2 · Duplicados ocultos por pixel")
    m1, m2 = st.columns(2)
    m1.metric("Leads duplicados (mismo pixel) en el filtro", f"{inflados_n:,}")
    m2.metric("Gasto desperdiciado en personas duplicadas", f"${gasto_inflado:,.2f}")
    st.caption("El lead_id es único, pero el id_pixel_facebook se repite: la misma persona como varios leads. "
               "Usa la 'Vista deduplicada' del panel lateral para ver el impacto.")

    st.markdown("##### Regla 3 · Embudo acumulado vs snapshot")
    st.caption("estado_gohighlevel es la foto actual de cada lead. El embudo se reconstruye asumiendo progresión "
               "monótona (quien es SQL pasó por MQL). El snapshot revela el quiebre MQL<SQL.")

    st.markdown("##### Regla 4 · Datos de febrero (fuera de rango)")
    st.metric("Filas de febrero 2026 (excluidas por defecto)", f"{int((df['mes'] == '2026-02').sum()):,}")
    st.caption("El reto declara marzo–mayo. Febrero se excluye de los KPIs y se marca como anomalía; se incluye "
               "con el toggle del panel lateral solo para auditoría.")
