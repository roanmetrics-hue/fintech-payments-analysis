"""
limpieza.py — Diagnóstico y limpieza de pagos_fintech.csv

"""

import pandas as pd


FALSOS_NULOS = ["", " ", "N/A", "NA", "n/a", "-", "?", "null"]

# Columnas que describen al cliente (no al pago) en el analisis dentro del cuaderno que use, me di cuenta que eran necesarias para hacer crosstab y encontrar similudes
COLS_CLIENTE = ["region_id", "status_customer", "risk_segment",
                "kyc_level", "income_bracket", "signup_dt"]



def cargar(ruta):
    """Lee el CSV sin dejar que pandas convierta textos en nulos.

    Por defecto, read_csv convierte el texto "None" en NaN. En kyc_level,
    "None" es un nivel válido.

    Recibe: la ruta del CSV (texto).
    Devuelve: el DataFrame cargado.
    """
    df = pd.read_csv(ruta, keep_default_na=False, na_values=[""])
    return df


def primer_valor(columna):
    """Devuelve el primer valor no vacío de una columna, o None si está toda vacía.

    La uso en diagnosticar() para la columna "ejemplo", así se ve cómo vienen
    los datos por dentro (formato de fechas, comas en los montos, etc.).

    Recibe: una columna (Series).
    Devuelve: el primer valor que no sea nulo, o None.
    """
    sin_vacios = columna.dropna()
    if len(sin_vacios) > 0:
        return sin_vacios.iloc[0]
    else:
        return None



def diagnosticar(df):
    """Devuelve una tabla de calidad con una fila por columna del DataFrame.

    Tiene el tipo de dato, los nulos, el porcentaje de nulos, los falsos nulos
    (textos como "N/A" o "-" que deberían ser nulos, de la lista FALSOS_NULOS),
    los valores únicos y un ejemplo del dato de cada columna, para ver formatos
    como el de las fechas. También imprime la suma de payment_id duplicados.

    Recibe: un DataFrame.
    Devuelve: la tabla de diagnóstico (DataFrame).
    Imprime: cuántos payment_id están repetidos.
    """
    diagnostico = pd.DataFrame({
        "tipo": df.dtypes.astype(str),
        "nulos": df.isna().sum(),
        "porc_nulos": (df.isna().mean() * 100).round(1),
        "falsos_nulos": df.isin(FALSOS_NULOS).sum(),
        "unicos": df.nunique(),
        "ejemplo": df.apply(primer_valor),
    })

    id_duplicados = df["payment_id"].duplicated().sum()
    print(f"payment_id repetidos: {id_duplicados}")

    return diagnostico



def limpiar(df):
    """Limpia el dataset de pagos: quita duplicados, convierte montos y fechas,
    corrige estados y monedas, y marca los casos dudosos sin borrarlos.

    Recibe: el DataFrame original (como sale de cargar).
    Devuelve: una copia limpia con 99 750 filas y 6 columnas de marcas (True/False):
    es_cargo_fijo, monto_atipico, fecha_pago_invalida, registro_invalido,
    registro_inconsistente y sin_cliente. No modifica el DataFrame original.

    Las decisiones de cada paso (problema, patrón, grado y decisión) están en
    la bitácora, debajo de esta función.
    """
    df = df.copy()

    # 1. Duplicados de payment_id
    repetido = df["payment_id"].duplicated(keep=False)
    normal = df["customer_id"] == df["payment_id"] + 1
    es_copia = repetido & ~normal
    df = df[~es_copia]
    df = df.reset_index(drop=True)

    # 2. payment_amount como número
    monto_texto = df["payment_amount"].str.replace(",", ".", regex=False)
    df["payment_amount"] = pd.to_numeric(monto_texto)

    # 2b. Montos negativos (-25)
    df["es_cargo_fijo"] = df["payment_amount"] == -25

    # 2c. Montos de 50 000
    df["monto_atipico"] = df["payment_amount"] == 50000

    # 3. payment_status mal escrito
    df["payment_status"] = df["payment_status"].replace("paidd", "paid")

    # 4. currency inconsistente
    df["currency"] = df["currency"].replace("EURO", "USD")
    df["currency"] = df["currency"].replace("USDT", "USD")

    # 5a. pay_dt imposible
    df["pay_dt"] = pd.to_datetime(df["pay_dt"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    df["fecha_pago_invalida"] = df["pay_dt"].isna()

    # 5b. signup_dt imposible
    # Primero guardo cuáles tenían algo escrito, porque después de convertir
    # ya no se puede distinguir un vacío de una fecha mal escrita.
    tenia_fecha = df["signup_dt"].notna()
    df["signup_dt"] = pd.to_datetime(df["signup_dt"], format="%Y-%m-%d", errors="coerce")
    df["registro_invalido"] = tenia_fecha & df["signup_dt"].isna()

    # 5c. Registro posterior al pago
    df["registro_inconsistente"] = df["signup_dt"] > df["pay_dt"]
    df.loc[df["registro_inconsistente"], "signup_dt"] = pd.NaT

    # 6. Pagos sin datos del cliente
    df["sin_cliente"] = df["status_customer"].isna()
    df["status_customer"] = df["status_customer"].fillna("Desconocido")
    df["risk_segment"] = df["risk_segment"].fillna("Desconocido")
    df["kyc_level"] = df["kyc_level"].fillna("Desconocido")
    df["income_bracket"] = df["income_bracket"].fillna("Desconocido")

    return df

# ======================================================================
# BITÁCORA DE limpiar()
# Cada número corresponde al paso con el mismo número dentro de la función.
# ======================================================================
#
# 1. payment_id DUPLICADOS
# Problema: 250 payment_id aparecen 2 veces, y las filas del par son distintas.
# Patrón: en el resto del dataset, customer_id = payment_id + 1. En los
#   250 pares, EXACTAMENTE una fila cumple esa regla (verificado: 1 → 250).
# Grado: certeza.
# Decisión: conservar la fila normal y quitar la copia (250 filas).
# No uso drop_duplicates() porque se quedaría con "la primera", y a veces
# la primera es la copia.
#
# 2. payment_amount COMO NÚMERO
# Problema: la columna es texto porque 6 019 montos vienen como "12,50".
# Patrón: siempre es el mismo valor; la coma es separador DECIMAL
# Grado: certeza.
# Decisión: cambiar la coma por punto y luego convertir (en ese orden).
#
# 2b. MONTOS NEGATIVOS (-25)
# Problema: 6 300 pagos de exactamente -25 (después de quitar duplicados).
# Patrón: todos del producto 1 (Wallet, 0 % de interés);
# Parece un cargo fijo; no se puede confirmar sin el negocio.
# Grado: supuesto.
# Decisión: NO borrar ni imputar. Marcar con es_cargo_fijo y excluirlos
#  del cálculo de dinero movido por pagos.
#
# 2c. MONTOS DE 50 000
# Problema: 56 pagos de exactamente 50 000 (después de quitar duplicados).
# Patrón: el resto de los pagos va de 9.99 a 48.99; 54 de los 56 son pagos sin cliente. Pense que eran en moneda de colombia al ser de la region 2, pero esos de la region 2
# solo caian en los duplicados por lo que al final opte por no convertir de peso colombianos a USD
# Grado: certeza.
# Decisión: conservar la fila (su estado sí sirve para tasas) y marcarla
# con monto_atipico para excluirla de los cálculos de dinero.
#
# 3. payment_status MAL ESCRITO
# Problema: pagos con estado "paidd".
# Patrón: no existe en el diccionario ese estado de pago
# Grado: certeza.
# Decisión: reemplazar por "paid".
#
# 4. currency INCONSISTENTE
# Problema: pagos en EURO y en USDT.
# Patrón: el catálogo dice que TODOS los productos son en USD; solo
#   aparecen en los productos 1 y 4; están repartidos en todas las
#   regiones (no se concentran en Europa); dentro de cada producto los
#   montos son idénticos a los de USD (misma mediana, mismos precios).
#   Si fuera otra moneda, los montos serían distintos.
# Grado: certeza.
# Decisión: error de captura. Cambiar la etiqueta a USD SIN convertir el
#   monto
#
# 5. FECHAS: pay_dt y signup_dt
# 5a. pay_dt: 5 549 pagos con "2024-02-30", fecha que no existe.
#   Es un valor fijo de relleno. Ninguna columna predice la fecha de un
#   pago (ni el producto ni el método ni el id), así que no se imputa.
#   Grado: certeza de que es inválida.
#   Decisión: NaT + marca fecha_pago_invalida. El pago se conserva
#
# 5b. signup_dt: 57 registros con "2024-13-40" (mes 13, día 40).
#   Decisión: NaT. No se imputa con la media: inventaría una fecha a
#   partir de una columna poco confiable.
#
# 5c. Registro posterior al pago: ~38 800 pagos ocurren ANTES de que el
#   cliente se registrara. Los pagos son del 1 al 24 de feb 2024; los
#   registros van de 2023 a dic 2024, mitad y mitad por año, lo que no
#   es creíble. pay_dt es la fecha confiable; signup_dt no.
#   Grado: acotado.
#   Decisión: NO borrar los pagos (el 40 % del dataset). Poner signup_dt
#   en NaT en esas filas y marcarlas. Este dataset no sirve para
#   analizar la antigüedad del cliente.
#
# 6. PAGOS SIN DATOS DEL CLIENTE
# Problema: 6 086 pagos (6 122 antes de quitar duplicados) sin región,
#   estado, riesgo, KYC, ingresos ni fecha de registro.
# Patrón: los datos del PAGO están completos; su customer_id es siempre
#   payment_id + 100 000 000 (fabricado por el sistema, no un cliente
#   real); todos están pagados; repartidos en tercios casi exactos en los
#   productos 1, 3 y 5 y en los 3 métodos. Parecen pagos de clientes que
#   no están en la base (p. ej. invitados o una carga externa).
# Grado: acotado.
# Decisión: conservarlos y marcarlos con sin_cliente. Borrarlos subiría
#   la tasa de fallidos de 12.2 % a 13.0 %, porque todos son pagados.
#   Las columnas de texto del cliente se rellenan con "Desconocido";
#   region_id y signup_dt quedan vacías (no se puede inventar un número
#   ni una fecha).



def resumen(antes, despues):
    """Compara el dataset antes y después de limpiar, con los números que le importan a la junta.

    Muestra las filas, el dinero movido y la tasa de fallidos antes y después;
    las filas eliminadas; los valores corregidos (montos con coma, estados "paidd"
    y monedas); y cada marca con lo que significa y 3 payment_id de ejemplo.

    Recibe: el DataFrame original y el limpio.
    Devuelve: nada; solo imprime.
    """

    # Filas
    print("Filas antes:", len(antes))
    print("Filas después:", len(despues))

    # Dinero movido antes: convierto el monto porque todavía es texto
    monto_texto = antes["payment_amount"].str.replace(",", ".", regex=False)
    monto_antes = pd.to_numeric(monto_texto)
    print("Dinero movido antes:", round(monto_antes.sum()))

    # Dinero movido después: sin cargos fijos ni montos atípicos
    pagos_normales = despues[~despues["es_cargo_fijo"] & ~despues["monto_atipico"]]
    print("Dinero movido después:", round(pagos_normales["payment_amount"].sum()))

    # Tasa de fallidos (fallidos + contracargos sobre el total)
    malos_antes = antes["payment_status"].isin(["failed", "chargeback"]).sum()
    malos_despues = despues["payment_status"].isin(["failed", "chargeback"]).sum()
    print("Tasa de fallidos antes:", round(malos_antes / len(antes) * 100, 1), "%")
    print("Tasa de fallidos después:", round(malos_despues / len(despues) * 100, 1), "%")

    # Filas eliminadas
    print()
    print("Filas eliminadas:", len(antes) - len(despues))
    print("   Copias de payment_id duplicados. En cada par se quedó la fila")
    print("   que cumple customer_id = payment_id + 1.")
    
    # Valores corregidos (se cuentan sobre los datos originales)
    print()
    print("Montos con coma convertidos:", antes["payment_amount"].str.contains(",").sum())
    print("   Venían como '12,50'; la coma se cambió por punto.")

    print()
    print("Estados 'paidd' corregidos:", (antes["payment_status"] == "paidd").sum())
    print("   Error de escritura; se cambiaron a 'paid'.")

    print()
    print("Monedas corregidas:", antes["currency"].isin(["EURO", "USDT"]).sum())
    print("   EURO y USDT eran errores de etiqueta; pasaron a USD sin convertir el monto.")

    # Marcas: qué es cada una, cuántas hay y algunos payment_id de ejemplo
    print()
    print("Cargos fijos (es_cargo_fijo):", despues["es_cargo_fijo"].sum())
    print("   Pagos de exactamente -25 USD, todos del producto 1 (Wallet).")
    print("   Posible comisión fija. Se conservan, pero no suman al dinero movido.")
    print("   Ejemplos:", list(despues.loc[despues["es_cargo_fijo"], "payment_id"].head(3)))

    print()
    print("Montos atípicos (monto_atipico):", despues["monto_atipico"].sum())
    print("   Pagos de exactamente 50 000 USD. El resto va de 9.99 a 48.99.")
    print("   Se conservan, pero no suman al dinero movido.")
    print("   Ejemplos:", list(despues.loc[despues["monto_atipico"], "payment_id"].head(3)))

    print()
    print("Fechas de pago inválidas (fecha_pago_invalida):", despues["fecha_pago_invalida"].sum())
    print("   Pagos con fecha 2024-02-30, que no existe. pay_dt quedó vacía.")
    print("   Ejemplos:", list(despues.loc[despues["fecha_pago_invalida"], "payment_id"].head(3)))

    print()
    print("Registros inválidos (registro_invalido):", despues["registro_invalido"].sum())
    print("   Clientes con fecha de registro 2024-13-40, que no existe. signup_dt quedó vacía.")
    print("   Ejemplos:", list(despues.loc[despues["registro_invalido"], "payment_id"].head(3)))

    print()
    print("Registros inconsistentes (registro_inconsistente):", despues["registro_inconsistente"].sum())
    print("   Pagos hechos ANTES de que el cliente se registrara, lo cual es imposible.")
    print("   signup_dt quedó vacía; el pago se conserva.")
    print("   Ejemplos:", list(despues.loc[despues["registro_inconsistente"], "payment_id"].head(3)))

    print()
    print("Pagos sin cliente (sin_cliente):", despues["sin_cliente"].sum())
    print("   Pagos completos sin región, estado, riesgo, KYC, ingresos ni registro.")
    print("   Su customer_id es payment_id + 100 000 000 (lo fabricó el sistema).")
    print("   Los datos de texto del cliente quedaron como 'Desconocido'.")
    print("   Ejemplos:", list(despues.loc[despues["sin_cliente"], "payment_id"].head(3)))


if __name__ == "__main__":
    ruta = "data/pagos_fintech.csv" #esto cambia si movemos el archivo de lugar

    original = cargar(ruta)
    print("=== DIAGNÓSTICO INICIAL ===")
    print(diagnosticar(original))
    print()

    limpio = limpiar(original)
    print("=== DIAGNÓSTICO FINAL ===")
    print(diagnosticar(limpio))
    print()

    print("=== EFECTO DE LA LIMPIEZA ===")
    resumen(original, limpio)

    limpio.to_csv("data/pagos_fintech_limpio.csv", index=False)
    print()
    print("Guardado en data/pagos_fintech_limpio.csv")

# REFLEXIÓN FINAL
# La decisión que más me costó fue la de los pagos de 50 000. Cuando los vi todos en la
# región 2, que es Andina (Colombia), pensé que eran pesos colombianos guardados como si
# fueran dólares, y casi los convierto. Pero cuando lo revisé con los datos no cuadraba:
# eran siempre exactamente 50 000, cuando un precio real en otra moneda tendría montos
# distintos; 221 de los 277 estaban en los payment_id duplicados; y la región 2 tenía más
# de 24 000 pagos normales en dólares. Si los hubiera convertido, habría inventado dinero.
# Aprendí que una hipótesis que suena lógica hay que probarla antes de tocar los datos, y
# que el patrón decide, no la primera idea que uno tiene.