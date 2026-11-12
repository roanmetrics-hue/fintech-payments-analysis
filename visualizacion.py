import os

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

plt.rcParams["text.parse_math"] = False
sns.set_theme(style="white")

CARPETA = "graficos"
GRIS = "#b0b0b0"
AZUL = "#1565c0"
NOMBRES_PRODUCTO = {"Loan": "Préstamo", "Wallet": "Cartera", "Card": "Tarjeta"}


def guardar(fig, nombre):
    """Guarda la figura en la carpeta de gráficos como PNG.

    Recibe: la figura y el nombre del archivo (sin la carpeta).
    Devuelve: nada. Crea la carpeta si no existe.
    """
    os.makedirs(CARPETA, exist_ok=True)
    fig.savefig(f"{CARPETA}/{nombre}", dpi=150, bbox_inches="tight")


def grafico_dinero_por_producto(tabla):
    """Barras horizontales del dinero movido por tipo de producto, con y sin los pagos de 50 000.

    Recibe: la tabla que devuelve dinero_por_producto_con_y_sin().
    Devuelve: la figura. La guarda en graficos/01_dinero_por_producto.png.
    """
    dinero = tabla.rename(index=NOMBRES_PRODUCTO).sort_values("sin_50000")

    y = np.arange(len(dinero))
    alto = 0.4

    fig, ax = plt.subplots(figsize=(10, 4.5))
    gris = ax.barh(y - alto / 2, dinero["con_50000"], height=alto, color=GRIS, label="Con los pagos de 50 000")
    azul = ax.barh(y + alto / 2, dinero["sin_50000"], height=alto, color=AZUL, label="Sin los pagos de 50 000")

    ax.set_yticks(y, dinero.index)
    ax.bar_label(gris, labels=[f"US${v / 1e6:.2f} M" for v in dinero["con_50000"]], padding=4, color="#808080")
    ax.bar_label(azul, labels=[f"US${v / 1e6:.2f} M" for v in dinero["sin_50000"]], padding=4)

    ax.set_title("Sin los pagos de 50 000, el préstamo mueve más dinero, no la tarjeta", loc="left", fontweight="bold")
    ax.set_xlabel("Dinero movido en febrero de 2024 (millones de US$)")
    ax.set_ylabel("Tipo de producto")
    ax.set_xlim(0, dinero["con_50000"].max() * 1.2)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v / 1e6:.1f}")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.15), ncol=2)

    plt.tight_layout()
    guardar(fig, "01_dinero_por_producto.png")
    return fig


def grafico_tasas_por_region(tabla):
    """Barras horizontales apiladas de la tasa de fallidos por región: failed + chargeback.

    Recibe: la tabla que devuelve tasa_fallidos_por_region().
    Devuelve: la figura. La guarda en graficos/02_tasas_por_region.png.
    No muestra "Sin región": son pagos sin cliente, todos pagados (0 %); se aclara en una nota.
    """
    tasas = tabla.drop(index="Sin región").sort_values("tasa_total")

    fig, ax = plt.subplots(figsize=(10, 4.5))
    rechazados = ax.barh(tasas.index, tasas["tasa_failed"], color=GRIS, label="Pagos rechazados (failed)")
    contracargos = ax.barh(tasas.index, tasas["tasa_chargeback"], left=tasas["tasa_failed"],
                           color=AZUL, label="Contracargos (chargeback)")

    # Cada pedazo con su valor adentro (si es muy chico no se escribe) y el total al final
    ax.bar_label(rechazados, labels=[f"{v:.1f} %" if v >= 2 else "" for v in tasas["tasa_failed"]],
                 label_type="center", color="white")
    ax.bar_label(contracargos, labels=[f"{v:.1f} %" if v >= 2 else "" for v in tasas["tasa_chargeback"]],
                 label_type="center", color="white")
    ax.bar_label(contracargos, labels=[f"Total {v:.1f} %" for v in tasas["tasa_total"]], padding=4)

    ax.set_title("Las regiones fallan parecido; Andina no registra ningún contracargo", loc="left", fontweight="bold")
    ax.set_xlabel("Pagos fallidos (% de los pagos normales de cada región)")
    ax.set_ylabel("Región")
    ax.set_xlim(0, tasas["tasa_total"].max() * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.15), ncol=2)

    n_sin_region = int(tabla.loc["Sin región", "n_pagos"])
    fig.text(0.01, -0.02, f"No se muestran {n_sin_region:,} pagos sin cliente (sin región): todos están pagados.".replace(",", " "),
             fontsize=9, color="#808080")

    plt.tight_layout()
    guardar(fig, "02_tasas_por_region.png")
    return fig


def grafico_tasas_por_riesgo(tabla):
    """Barras horizontales apiladas de la tasa de fallidos por segmento de riesgo: failed + chargeback.

    Recibe: la tabla que devuelve fallidos_por_riesgo().
    Devuelve: la figura. La guarda en graficos/03_tasas_por_riesgo.png.
    Los segmentos van en su orden natural (bajo, medio, alto), no por valor, porque es una escala.
    No muestra "Desconocido": son pagos sin cliente, todos pagados (0 %); se aclara en una nota.
    """
    orden = ["Low", "Medium", "High"]
    nombres = {"Low": "Bajo", "Medium": "Medio", "High": "Alto"}
    tasas = tabla.loc[orden].rename(index=nombres)

    fig, ax = plt.subplots(figsize=(10, 4))
    rechazados = ax.barh(tasas.index, tasas["tasa_failed"], color=GRIS, label="Pagos rechazados (failed)")
    contracargos = ax.barh(tasas.index, tasas["tasa_chargeback"], left=tasas["tasa_failed"],
                           color=AZUL, label="Contracargos (chargeback)")

    # Cada pedazo con su valor adentro (si es muy chico no se escribe) y el total al final
    ax.bar_label(rechazados, labels=[f"{v:.1f} %" if v >= 2 else "" for v in tasas["tasa_failed"]],
                 label_type="center", color="white")
    ax.bar_label(contracargos, labels=[f"{v:.1f} %" if v >= 2 else "" for v in tasas["tasa_chargeback"]],
                 label_type="center", color="white")
    ax.bar_label(contracargos, labels=[f"Total {v:.1f} %" for v in tasas["tasa_total"]], padding=4)

    ax.set_title("El riesgo alto falla por contracargos; el medio, por pagos rechazados", loc="left", fontweight="bold")
    ax.set_xlabel("Pagos fallidos (% de los pagos normales de cada segmento)")
    ax.set_ylabel("Riesgo del cliente")
    ax.set_xlim(0, tasas["tasa_total"].max() * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.17), ncol=2)

    n_desconocido = int(tabla.loc["Desconocido", "n_pagos"])
    fig.text(0.01, -0.03, f"No se muestran {n_desconocido:,} pagos sin cliente (riesgo desconocido): todos están pagados.".replace(",", " "),
             fontsize=9, color="#808080")

    plt.tight_layout()
    guardar(fig, "03_tasas_por_riesgo.png")
    return fig


def grafico_mapa_producto_metodo(tabla):
    """Mapa de calor del dinero movido por tipo de producto y método de pago.

    Recibe: la tabla que devuelve dinero_por_producto_y_metodo() (con fila y columna "Total").
    Devuelve: la figura. La guarda en graficos/04_mapa_producto_metodo.png.
    Las combinaciones que no existen (0) se dejan en blanco. Los totales van en las etiquetas.
    """
    nombres_metodo = {"card": "Pago con tarjeta", "cash": "Efectivo", "transfer": "Transferencia"}

    totales_producto = tabla["Total"].drop("Total")
    totales_metodo = tabla.loc["Total"].drop("Total")
    celdas = tabla.drop(index="Total", columns="Total")

    # Etiquetas de los ejes con el total de cada fila y columna
    filas = [f"{NOMBRES_PRODUCTO[p]}\n(US${totales_producto[p] / 1e6:.2f} M)" for p in celdas.index]
    columnas = [f"{nombres_metodo[m]}\n(US${totales_metodo[m] / 1e6:.2f} M)" for m in celdas.columns]

    textos = celdas.map(lambda v: f"US${v / 1000:,.0f} mil".replace(",", " ") if v > 0 else "")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    sns.heatmap(celdas, mask=(celdas == 0), annot=textos, fmt="", cmap="Blues", vmin=0,
                cbar=False, linewidths=2, linecolor="white", ax=ax,
                xticklabels=columnas, yticklabels=filas)

    ax.set_title("El método de pago depende del producto: la transferencia solo se usa en la tarjeta",
                 loc="left", fontweight="bold")
    ax.set_xlabel("Método de pago")
    ax.set_ylabel("Tipo de producto")
    ax.tick_params(axis="y", rotation=0)
    ax.tick_params(axis="x", rotation=0)

    fig.text(0.01, -0.03, "Dinero movido en febrero de 2024 (US$), solo pagos normales. "
             "Las celdas en blanco son combinaciones que no existen.", fontsize=9, color="#808080")

    plt.tight_layout()
    guardar(fig, "04_mapa_producto_metodo.png")
    return fig