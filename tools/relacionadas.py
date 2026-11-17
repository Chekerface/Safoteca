#!/usr/bin/env python3
"""Obras relacionadas: UNA sola fórmula para la ficha de la web y para las páginas de buscadores.

La calcula tools/exportar_json.py y la guarda en obras.json («rel»: ids de las más parecidas, de más a menos).
La web enseña las 10 primeras que no tengan avisos que la persona evita; las páginas por obra, las 6 primeras.

Cómo puntúa (los números se ajustan aquí, en AJUSTES):
  * Temáticas en común, según lo raras que son: compartir «Vampiras» (pocas obras) vale mucho; compartir
    «Adolescencia» (casi 100 obras), poco. Rareza = ln(obras publicadas / obras con esa temática). Como mucho
    4 puntos en total; a igualdad de puntos desempata lo que compartan en temáticas sin ese tope.
  * Géneros en común: 1 + su rareza, multiplicado por lo definitorio que es el género para las dos obras
    (1 / raíz(nº de géneros de una × nº de géneros de la otra)); como mucho 3 puntos en total. Dos obras que solo
    son «Drama» se parecen más que dos que son «Drama» entre otros cinco géneros.
  * Misma dirección, actrices en común y el mismo nivel de representación (A, B o C) suman aparte.
  * Hay que parecerse en algo concreto: temáticas suficientemente raras, alguna temática más un género
    definitorio, un género muy raro, o la misma directora o actriz. Compartir solo géneros comunes no basta.
  * Si la obra tiene final feliz, solo se recomiendan obras con final feliz.
  * Desempates: mismo tipo (serie/película), nivel de relevancia y año. Al final se ordenan poniendo primero
    las del mismo tipo (si la ficha es una serie, las series delante y las películas detrás).
"""
import math
from collections import Counter

AJUSTES = {
    "max": 20,                 # cuántas se guardan (la web enseña 10 y las páginas 6, tras quitar las evitadas)
    "peso_tematica": 1.0,      # multiplica la rareza de cada temática en común...
    "tope_tematicas": 4.0,     # ...con este máximo de puntos entre todas las temáticas
    "peso_genero": 1.0,        # multiplica (1 + rareza) × especificidad de cada género en común...
    "tope_generos": 3.0,       # ...con este máximo de puntos entre todos los géneros
    "genero_raro": 5,          # un género con este nº de obras o menos cuenta como «algo concreto»
    "minimo_tematicas": 2.5,   # puntos de temáticas para contar como «algo concreto»
    "direccion": 3.0,          # misma directora/director
    "actriz": 1.5,             # por actriz en común
    "mismo_tipo": 0.5,         # serie con serie, película con película
    "mismo_nivel": 1.0,        # mismo nivel de representación (A con A, B con B, C con C)
    "exigir_final_feliz": True,
}
REL = {"A": 3, "B": 2, "C": 1}


def calcular(obras, ajustes=None):
    """Devuelve {id: [ids relacionadas]} para una lista de obras con el formato de obras.json."""
    A = dict(AJUSTES, **(ajustes or {}))
    n = max(len(obras), 1)
    df_t = Counter(t for o in obras for t in set(o.get("tematicas") or []))
    df_g = Counter(g for o in obras for g in set(o.get("generos") or []))
    rareza = lambda df, x: math.log(n / df[x]) if df[x] else 0.0
    res = {}
    for o in obras:
        tem, gen = set(o.get("tematicas") or []), set(o.get("generos") or [])
        dirs, acts = set(o.get("directores") or []), set(o.get("actrices") or [])
        cand = []
        for c in obras:
            if c["id"] == o["id"]:
                continue
            if A["exigir_final_feliz"] and o.get("final_feliz") is True and c.get("final_feliz") is not True:
                continue
            t_com = tem & set(c.get("tematicas") or [])
            g_com = gen & set(c.get("generos") or [])
            p_tem = A["peso_tematica"] * sum(rareza(df_t, t) for t in t_com)
            # cada género en común: 1 + su rareza, multiplicado por lo «definitorio» que es para las dos obras
            # (1 si ambas tienen un solo género; 0,5 si tienen 2 y 2; casi nada si tienen muchos)
            esp = 1 / math.sqrt(max(len(gen), 1) * max(len(set(c.get("generos") or [])), 1))
            p_gen = min(A["tope_generos"], A["peso_genero"] * sum(1 + rareza(df_g, g) for g in g_com) * esp)
            p_dir = A["direccion"] if dirs & set(c.get("directores") or []) else 0.0
            p_act = A["actriz"] * len(acts & set(c.get("actrices") or []))
            concreto = (p_tem >= A["minimo_tematicas"] or p_dir or p_act
                        or (p_tem > 0 and p_tem + p_gen >= A["minimo_tematicas"])   # alguna temática + género definitorio
                        or any(df_g[g] <= A["genero_raro"] for g in g_com))
            if not concreto:
                continue
            mismo = c.get("tipo") == o.get("tipo")
            nivel = A["mismo_nivel"] if o.get("relevancia") and o.get("relevancia") == c.get("relevancia") else 0.0
            pts = min(A["tope_tematicas"], p_tem) + p_gen + p_dir + p_act + (A["mismo_tipo"] if mismo else 0.0) + nivel
            # a igualdad de puntos, desempata lo que comparten en temáticas sin tope (para no ordenar al azar)
            cand.append((-round(pts, 3), -mismo, -round(p_tem, 3), -REL.get(c.get("relevancia"), 0), -(c.get("anio") or 0), c["id"]))
        cand.sort()
        # dentro de las elegidas, primero las del mismo tipo (series con series, películas con películas),
        # cada grupo en su orden de parecido
        top = cand[:A["max"]]
        res[o["id"]] = [x[-1] for x in sorted(top, key=lambda x: x[1])]
    return res
