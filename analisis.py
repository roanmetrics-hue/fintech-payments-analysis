import numpy as np
import pandas as pd
 
RUTA_PRODUCTOS = "data/productos.csv"
RUTA_REGIONES = "data/regiones.csv"
 
 
def transformar(df):
    """Une los pagos limpios con los catálogos y agrega las columnas de análisis.
 
    Recibe: el DataFrame que devuelve limpiar().
    Devuelve: una copia con product_type, interest_rate, region_name, country,
    dia_semana, dia, rango_monto, y las marcas es_normal, es_fallido,
    es_failed y es_chargeback.
    Verifica que los merges no pierdan ni dupliquen filas.
    """
    df = df.copy()
    filas_antes = len(df)
 
    # 1. Merge con productos. Solo traigo las columnas que aportan:
    #    currency ya existe en pagos y quedaría duplicada.
    productos = pd.read_csv(RUTA_PRODUCTOS)[["product_id", "product_type", "interest_rate"]]
    df = df.merge(productos, on="product_id", how="left", validate="many_to_one", indicator=True)
    print("Merge productos:", df["_merge"].value_counts().to_dict())
    df = df.drop(columns="_merge")
 
    # 2. Merge con regiones. Los pagos sin cliente no tienen region_id:
    #    quedan como "Sin región" para que el groupby no los descarte.
    regiones = pd.read_csv(RUTA_REGIONES)[["region_id", "region_name", "country"]]
    df = df.merge(regiones, on="region_id", how="left", validate="many_to_one", indicator=True)
    print("Merge regiones:", df["_merge"].value_counts().to_dict())
    df = df.drop(columns="_merge")
    df["region_name"] = df["region_name"].fillna("Sin región")
 
    # Control: los merges no deben cambiar el número de filas
    assert len(df) == filas_antes, "Un merge cambió el número de filas"
 
    # 3. Tiempo. Todos los pagos son de febrero de 2024, así que no se crea una columna de mes.
    #    Las fechas "2024-02-30" quedan sin dia_semana ni dia (NaT).

    df["dia_semana"] = df["pay_dt"].dt.day_name()
    df["dia"] = df["pay_dt"].dt.floor("D")
 
    # 4. Pagos normales: todo lo que no es cargo fijo (-25) ni monto atípico (50 000).
    #    Se define una sola vez aquí y todas las funciones de análisis la usan.
    df["es_normal"] = ~(df["es_cargo_fijo"] | df["monto_atipico"])
 
    # 5. Rango de monto con cuartiles de los pagos normales.
    #    Los -25 y los 50 000 tienen su propia categoría para no contaminar los rangos.
    q1, q3 = df.loc[df["es_normal"], "payment_amount"].quantile([0.25, 0.75])
    condiciones = [
        df["es_cargo_fijo"],
        df["monto_atipico"],
        df["payment_amount"] <= q1,
        df["payment_amount"] <= q3,
    ]
    etiquetas = ["Cargo fijo", "Atípico", "Bajo", "Medio"]
    df["rango_monto"] = np.select(condiciones, etiquetas, default="Alto")
 
    # 6. Pagos fallidos: failed y chargeback juntos, y cada uno por separado
    df["es_fallido"] = df["payment_status"].isin(["failed", "chargeback"])
    df["es_failed"] = df["payment_status"] == "failed"
    df["es_chargeback"] = df["payment_status"] == "chargeback"
 
    return df
 
 
 
def tasa_fallidos_por_region(df):
    """Tasa de pagos fallidos y de contracargos por región.
 
    Recibe: el DataFrame que devuelve transformar().
    Devuelve: una tabla con una fila por región: número de pagos, tasa de
    failed, tasa de chargeback y tasa total (failed + chargeback), en %.
    Ordenada de la tasa total más alta a la más baja.
    """
    df = df[df["es_normal"]]
 
    tabla = df.groupby("region_name").agg(
        n_pagos=("payment_id", "count"),
        tasa_failed=("es_failed", "mean"),
        tasa_chargeback=("es_chargeback", "mean"),
        tasa_total=("es_fallido", "mean"),
    )
 
    columnas_tasa = ["tasa_failed", "tasa_chargeback", "tasa_total"]
    tabla[columnas_tasa] = (tabla[columnas_tasa] * 100).round(2)
 
    return tabla.sort_values("tasa_total", ascending=False)
 
# Respuesta: 
# ¿Qué región tiene la mayor tasa de pagos fallidos y de contracargos?
#
# La tasa se calcula solo con los pagos normales: se excluyen los cargos fijos de -25 y los
# montos atípicos de 50 000, porque no son pagos que el cliente intenta hacer y todos están en "paid".
#
# Europa tiene la tasa más alta: 14.80 % (11.02 % failed + 3.78 % chargeback), pero está prácticamente
# empatada con Norteamérica (14.76 %) y Caribe (14.71 %). Entre estas tres no hay una diferencia real.
#
# La tasa de failed es casi igual en las cuatro regiones (entre 11.02 % y 11.27 %). Lo que separa a
# las regiones son los contracargos.
#
# Andina es la única que se separa: 11.27 %, porque tiene 0 contracargos en 21 873 pagos, mientras
# que las otras tres tienen entre 3.65 % y 3.78 %. Norteamérica vende los mismos productos que Andina
# (1, 3 y 5) y sí tiene contracargos, así que no se explica por el producto. Hay que preguntar si el
# sistema registra contracargos en esa región (supuesto).
#
# Con y sin: si se incluyen los -25, Norteamérica bajaba a 12.99 % y Andina a 10.09 %. Los cargos
# fijos son todos del producto 1 (que solo se vende en esas dos regiones) y todos están pagados,
# así que bajaban artificialmente su tasa.
#
# Los 5 280 pagos "Sin región" tienen 0 % de fallidos porque todos son pagos sin cliente y todos
# están pagados. Se muestran aparte.
 
######################################################
 
def dinero_por_producto_y_metodo(df):
    """Dinero movido por tipo de producto y método de pago.
 
    Recibe: el DataFrame que devuelve transformar().
    Devuelve: una tabla cruzada (pivot_table) con el tipo de producto en las filas,
    el método de pago en las columnas y la suma de payment_amount (US$) en cada celda.
    Incluye la fila y la columna "Total". Las combinaciones que no existen quedan en 0.
    Solo usa los pagos normales: excluye los cargos fijos de -25 y los montos atípicos de 50 000.
    """
    normales = df[df["es_normal"]]
 
    tabla = normales.pivot_table(
        values="payment_amount",
        index="product_type",
        columns="pay_method",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="Total",
    ).round(0)
 
    # Ordena los productos de mayor a menor, dejando la fila Total al final
    orden = tabla.drop(index="Total").sort_values("Total", ascending=False).index.tolist()
    return tabla.loc[orden + ["Total"]]
 
# Respuesta: ¿Qué tipo de producto y qué método de pago mueven más dinero?
#
# Se usan solo los pagos normales (sin los cargos fijos de -25 ni los montos atípicos de 50 000).
#
# Producto: el préstamo (Loan) mueve más dinero, US$901 107, seguido de cerca por la cartera
# (US$880 956) y la tarjeta (US$815 568). La diferencia es pequeña y viene de la cantidad de
# pagos (32 477 contra 31 484 y 29 433), no del monto: la mediana de un pago es de unos US$28
# en los tres productos.
#
# Método: la tarjeta mueve más, US$976 243, contra US$815 568 de la transferencia y US$805 821
# del efectivo. Pero el método está atado al producto: la transferencia solo se usa para pagar
# Card, y la tarjeta y el efectivo solo para Loan y Wallet. La tarjeta gana porque la usan dos
# productos, no porque los clientes la prefieran.
#
# Con y sin: con los 50 000 incluidos, el ganador cambia en las dos preguntas (Card y
# transferencia, con US$1.97 millones cada uno) y el total pasa de US$2.6 a US$5.4 millones.
# Unos pocos montos falsos decidían el resultado.
 
##########################################
 
def fallidos_por_riesgo(df):
    """Tasa de pagos fallidos y de contracargos por segmento de riesgo del cliente.
 
    Recibe: el DataFrame que devuelve transformar().
    Devuelve: una tabla con una fila por segmento de riesgo (High, Medium, Low y
    Desconocido): número de pagos, tasa de failed, tasa de chargeback y tasa total, en %.
    Solo usa los pagos normales: excluye los cargos fijos de -25 y los montos atípicos de 50 000.
    """
    df = df[df["es_normal"]]
 
    tabla = df.groupby("risk_segment").agg(
        n_pagos=("payment_id", "count"),
        tasa_failed=("es_failed", "mean"),
        tasa_chargeback=("es_chargeback", "mean"),
        tasa_total=("es_fallido", "mean"),
    )
 
    columnas_tasa = ["tasa_failed", "tasa_chargeback", "tasa_total"]
    tabla[columnas_tasa] = (tabla[columnas_tasa] * 100).round(2)
 
    return tabla.sort_values("tasa_total", ascending=False)
 
# Respuesta: ¿Los clientes de riesgo alto fallan más que los de riesgo bajo?
#
# Se usan solo los pagos normales (sin los cargos fijos de -25 ni los montos atípicos de 50 000).
#
# Sí. Los clientes de riesgo alto tienen una tasa total de 18.62 %, contra 10.86 % del riesgo
# bajo: fallan 1.7 veces más.
#
# Pero el riesgo medio está casi igual que el alto (18.35 %) y fallan de forma distinta:
# - High falla sobre todo por contracargos: 12.32 % chargeback y solo 6.29 % failed.
# - Medium falla solo por pagos rechazados: 18.35 % failed y 0 % chargeback.
# Para la fintech no es lo mismo: un failed es un pago que no entró, y un chargeback es dinero
# que entró y después se devolvió.
#
# Que el riesgo medio tenga 0 contracargos en 21 850 pagos es sospechoso, igual que Andina.
# Hay que preguntar si el sistema registra contracargos para ese segmento (supuesto).
#
# Los 5 280 pagos con riesgo "Desconocido" son pagos sin cliente: todos están pagados y tienen
# 0 % de fallidos. Se muestran aparte.

############################################

##########################################

def dinero_por_producto_con_y_sin(df):
    """Dinero movido por tipo de producto, con y sin los pagos de 50 000.

    muestra cómo cambia la respuesta
    según se incluyan o no los montos atípicos.

    Recibe: el DataFrame que devuelve transformar().
    Devuelve: una tabla con una fila por tipo de producto y dos columnas en US$:
    con_50000 (todos los pagos menos los cargos fijos de -25) y sin_50000 (solo pagos normales).
    En las dos se excluyen los -25, para que la única diferencia sean los pagos de 50 000.
    """
    tabla = pd.DataFrame({
        "con_50000": df[~df["es_cargo_fijo"]].groupby("product_type")["payment_amount"].sum(),
        "sin_50000": df[df["es_normal"]].groupby("product_type")["payment_amount"].sum(),
    }).round(0)

    return tabla.sort_values("sin_50000", ascending=False)

# Respuesta: ¿Cambia la respuesta de la pregunta 2 si se incluyen los pagos de 50 000?
#
# Sí. Con los pagos de 50 000, la tarjeta (Card) parece mover más dinero: US$1.97 millones,
# casi empatada con el préstamo (US$1.95 M). Sin ellos, la tarjeta pasa al último lugar
# (US$0.82 M) y el préstamo es el primero (US$0.90 M).
# Son solo 56 pagos (23 en Card, 21 en Loan y 12 en Wallet), pero cada uno vale lo que unos
# 1 800 pagos normales, así que deciden el ranking. Por eso las conclusiones se dan sin ellos.


##########################################

DIAS_ORDEN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DIAS_ES = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves",
           "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}


def fallidos_por_dia_semana(df):
    """Tasa de pagos fallidos y de contracargos por día de la semana.

    Recibe: el DataFrame que devuelve transformar().
    Devuelve: una tabla con una fila por día (de lunes a domingo): cuántas fechas
    de ese día hay en los datos, número de pagos, tasa de failed, tasa de
    chargeback y tasa total, en %.
    Solo usa los pagos normales con fecha válida: los 2024-02-30 no tienen día.
    """
    df = df[df["es_normal"] & ~df["fecha_pago_invalida"]]

    tabla = df.groupby("dia_semana").agg(
        n_fechas=("dia", "nunique"),
        n_pagos=("payment_id", "count"),
        tasa_failed=("es_failed", "mean"),
        tasa_chargeback=("es_chargeback", "mean"),
        tasa_total=("es_fallido", "mean"),
    )

    columnas_tasa = ["tasa_failed", "tasa_chargeback", "tasa_total"]
    tabla[columnas_tasa] = (tabla[columnas_tasa] * 100).round(2)

    # Orden natural de la semana, no por valor
    return tabla.reindex(DIAS_ORDEN).rename(index=DIAS_ES)


def fallidos_por_fecha_valida(df):
    """Compara la tasa de fallidos de los pagos con fecha válida y con fecha 2024-02-30.

    Sirve para saber si sacar las fechas inválidas del análisis por día cambia el resultado.

    Recibe: el DataFrame que devuelve transformar().
    Devuelve: una tabla con dos filas (fecha válida / fecha 2024-02-30): número de
    pagos, tasa de failed, tasa de chargeback y tasa total, en %.
    Solo usa los pagos normales.
    """
    df = df[df["es_normal"]]

    tabla = df.groupby("fecha_pago_invalida").agg(
        n_pagos=("payment_id", "count"),
        tasa_failed=("es_failed", "mean"),
        tasa_chargeback=("es_chargeback", "mean"),
        tasa_total=("es_fallido", "mean"),
    )

    columnas_tasa = ["tasa_failed", "tasa_chargeback", "tasa_total"]
    tabla[columnas_tasa] = (tabla[columnas_tasa] * 100).round(2)

    tabla.index = tabla.index.map({False: "Fecha válida", True: "Fecha 2024-02-30"})
    return tabla

# Respuesta: ¿Cambia la tasa de fallidos según el día de la semana?
#
# Se usan solo los pagos normales con fecha válida (sin -25, sin 50 000 y sin "2024-02-30"):
# 87 858 pagos.
#
# No. La tasa total va de 12.67 % (sábado) a 13.41 % (viernes): menos de 1 punto entre el
# día más alto y el más bajo. Los pagos rechazados se quedan entre 10.13 % y 10.65 %, y los
# contracargos entre 2.41 % y 2.76 %, todos los días. Con unos 11 000 pagos por día, una
# diferencia así puede ser azar, igual que el empate entre Europa, Norteamérica y Caribe.
#
# Límites:
# - Solo hay un mes (del 1 al 24 de febrero de 2024). El 1 fue jueves, así que jueves,
#   viernes y sábado aparecen 4 veces y los demás días 3 (columna n_fechas). El sábado tiene
#   4 fechas pero solo 11 835 pagos, contra unos 15 000 de jueves y viernes, porque el 24
#   termina a las 3:33 a. m.
# - Los 5 536 pagos normales con fecha "2024-02-30" fallan más: 15.16 % contra 12.98 % de
#   los que tienen fecha válida (12.14 % failed y 3.02 % chargeback). No se sabe a qué día
#   pertenecen, así que si se concentraran en un día podrían cambiar el resultado. Que fallen
#   más hace pensar que el sistema no pone esa fecha al azar; hay que preguntarle al negocio
#   (supuesto).