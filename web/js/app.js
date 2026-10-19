/* La Safoteca · aplicación (sin dependencias, sin servidores)
   Lee web/data/obras.json y web/data/catalogos.json.
   Favoritos y preferencias se guardan solo en el dispositivo de cada persona. */
(() => {
  "use strict";

  const CFG = window.SAFOTECA_CONFIG || {};
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = (s) => String(s ?? "").normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
  const seguro = (u) => /^https?:\/\//i.test(u);

  // ---------- Almacenamiento local (nunca falla si el navegador lo bloquea) ----------
  const memoria = {};
  const guardar = {
    leer(k, def) {
      try { const v = localStorage.getItem("safoteca." + k); return v === null ? def : JSON.parse(v); }
      catch { return k in memoria ? memoria[k] : def; }
    },
    escribir(k, v) {
      memoria[k] = v;
      try { localStorage.setItem("safoteca." + k, JSON.stringify(v)); } catch { /* sin almacenamiento */ }
    },
    borrar() {
      Object.keys(memoria).forEach((k) => delete memoria[k]);
      try { Object.keys(localStorage).filter((k) => k.startsWith("safoteca.")).forEach((k) => localStorage.removeItem(k)); } catch { /* nada */ }
    },
  };

  // ---------- Estado ----------
  const E = {
    obras: [], porId: new Map(), cat: { generos: [], tematicas: [], avisos: [] }, meta: {},
    favs: new Set(guardar.leer("favs", [])),
    evitar: new Set(guardar.leer("evitar", [])),
    verAvisos: guardar.leer("verAvisos", false),
    introVista: guardar.leer("intro", false),
    campanaCerrada: guardar.leer("campana", ""),
    cargado: false, navegado: false, abrirAlCargar: null, evitarCambiado: false, F: null,
  };

  // ---------- Iconos ----------
  const svg = (d, extra = "") => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${d}</svg>`;
  const ICONO = {
    menu: svg('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    atras: svg('<path d="M15 5l-7 7 7 7"/>'),
    filtro: svg('<path d="M4 5h16l-6.500 8v5.500L10.500 20v-7z"/>'),
    inicio: svg('<path d="M4 11l8-7 8 7v8.500a1 1 0 0 1-1 1h-4V15H9v5.500H5a1 1 0 0 1-1-1z"/>'),
    claqueta: svg('<rect x="3" y="9" width="18" height="11" rx="2"/><path d="M3 9l2.500-4.500h4L7 9M9.500 9L12 4.500h4L13.500 9M16 9l2.500-4.500H21"/>'),
    corazon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.500s-8-4.900-8-11.200A4.600 4.600 0 0 1 12 6.800a4.600 4.600 0 0 1 8 2.500c0 6.300-8 11.200-8 11.200z"/></svg>',
    lupa: svg('<circle cx="11" cy="11" r="6.500"/><path d="M16 16l4.500 4.500"/>'),
    cerrar: svg('<path d="M6 6l12 12M18 6L6 18"/>'),
    bandera: svg('<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>', 'width="18" height="18"'),
    fuera: svg('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>', 'width="18" height="18"'),
  };

  // ---------- Utilidades de datos ----------
  const TIPO = { serie: "Serie", pelicula: "Película", libro: "Libro", comic: "Cómic" };
  const PLATAFORMAS = {
    "netflix.com": "Netflix", "primevideo.com": "Prime Video", "amazon.es": "Amazon", "amazon.com": "Amazon",
    "disneyplus.com": "Disney+", "hbomax.com": "HBO Max", "max.com": "Max", "filmin.es": "Filmin", "filmin.com": "Filmin",
    "rtve.es": "RTVE Play", "youtube.com": "YouTube", "youtu.be": "YouTube", "vimeo.com": "Vimeo",
    "tv.apple.com": "Apple TV+", "movistarplus.es": "Movistar Plus+", "atresplayer.com": "Atresplayer",
    "mitele.es": "Mitele", "crunchyroll.com": "Crunchyroll", "paramountplus.com": "Paramount+", "mubi.com": "MUBI",
  };
  const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };
  const nombreSitio = (u) => {
    const h = host(u);
    const k = Object.keys(PLATAFORMAS).find((d) => h === d || h.endsWith("." + d));
    return k ? PLATAFORMAS[k] : h;
  };
  // Plataformas: el exportador reconoce cada enlace (n = plataforma, p = país de 2 letras o INT, u = enlace).
  const PAIS = { ES: "España", US: "EE. UU.", GB: "Reino Unido", CA: "Canadá", JP: "Japón", MX: "México", PA: "Panamá", FR: "Francia", DE: "Alemania", IT: "Italia", PT: "Portugal", AR: "Argentina", CO: "Colombia", CL: "Chile", AU: "Australia" };
  const delPais = (x) => x.p === "ES" || x.p === "INT";            // plataformas que se muestran siempre
  const clavePlat = (x) => (delPais(x) ? x.n : `${x.n} · ${PAIS[x.p] || x.p}`);
  const anios = (o) => (o.anio ? (o.anio_fin ? `${o.anio}–${o.anio_fin}` : `${o.anio}`) : "");
  const edadNum = (o) => (o.edad == null ? null : o.edad === "TP" ? 0 : parseInt(o.edad, 10));
  const textoEdad = (o) => (o.edad == null ? "" : o.edad === "TP" ? "Todos los públicos" : `+${o.edad}`);
  const az = (a, b) => norm(a.titulo).localeCompare(norm(b.titulo), "es");

  // Evitar un aviso ignora mayúsculas, tildes y puntuación ("Sindrome de la lesbiana muerta." cuenta como
  // "Síndrome de la lesbiana muerta"). Las etiquetas se muestran siempre tal cual están en los datos.
  const claveAviso = (n) => norm(n).replace(/[^\p{L}\p{N}\s]/gu, "").replace(/\s+/g, " ").trim();
  const tieneEvitado = (o) => o.avisos.some((a) => E.evitar.has(claveAviso(a.nombre)));
  const visibles = () => E.obras.filter((o) => !tieneEvitado(o));
  const ocultas = () => E.obras.length - visibles().length;

  // ---------- Filtros (viven en la dirección: se pueden compartir) ----------
  const separar = (v) => (v || "").split("|").filter(Boolean);
  function filtrosDe(p) {
    return {
      q: p.get("q") || "", tipo: p.get("tipo") || "", gen: separar(p.get("gen")), tem: separar(p.get("tem")),
      rel: separar(p.get("rel")), final: p.get("final") === "si" ? "si" : "", plat: separar(p.get("plat")), otros: p.get("otros") === "1",
      edad: p.get("edad") ?? "", orden: p.get("orden") || "az",
    };
  }
  function paramsDe(f) {
    const p = new URLSearchParams();
    if (f.q) p.set("q", f.q);
    if (f.tipo) p.set("tipo", f.tipo);
    if (f.gen.length) p.set("gen", f.gen.join("|"));
    if (f.tem.length) p.set("tem", f.tem.join("|"));
    if (f.rel.length) p.set("rel", f.rel.join("|"));
    if (f.final) p.set("final", f.final);
    if (f.plat.length) p.set("plat", f.plat.join("|"));
    if (f.otros) p.set("otros", "1");
    if (f.edad !== "") p.set("edad", f.edad);
    if (f.orden !== "az") p.set("orden", f.orden);
    return p.toString();
  }
  const activos = (f) => (f.q ? 1 : 0) + (f.tipo ? 1 : 0) + f.gen.length + f.tem.length + f.rel.length + (f.final ? 1 : 0) + f.plat.length + (f.edad !== "" ? 1 : 0);

  function filtrar(f) {
    const q = norm(f.q).trim();
    const max = f.edad === "" ? null : Number(f.edad);
    const r = visibles().filter((o) => {
      if (f.tipo && o.tipo !== f.tipo) return false;
      if (f.rel.length && !f.rel.includes(o.relevancia)) return false;
      if (f.final && o.final_feliz !== true) return false;
      if (f.gen.length && !f.gen.some((g) => o.generos.includes(g))) return false;
      if (f.tem.length && !f.tem.some((t) => o.tematicas.includes(t))) return false;
      if (f.plat.length && !(o.plataformas || []).some((x) => f.plat.includes(clavePlat(x)) && (f.otros || delPais(x)))) return false;
      if (max !== null) { const n = edadNum(o); if (n !== null && n > max) return false; }
      if (q && !o._h.includes(q)) return false;
      return true;
    });
    const orden = {
      az,
      recientes: (a, b) => (b.anio || 0) - (a.anio || 0) || (b.publicada || "").localeCompare(a.publicada || "") || az(a, b),
      relevancia: (a, b) => String(a.relevancia || "Z").localeCompare(String(b.relevancia || "Z")) || az(a, b),
    }[f.orden] || az;
    return r.sort(orden);
  }

  // ---------- Piezas de interfaz ----------
  function poster(o, grande = false) {
    const tono = 250 + ((o.id * 47) % 80);
    if (!o.poster) return `<div class="poster poster--vacio" style="--tono:${tono}"><span>${esc(o.titulo)}</span></div>`;
    const w = grande ? 600 : 300;
    return `<img class="poster" src="img/${esc(o.poster)}_${w}.webp" alt="${grande ? "Póster de " + esc(o.titulo) : ""}" width="${w}" height="${w * 1.5}" ${grande ? "" : 'loading="lazy"'} decoding="async" data-tono="${tono}" data-titulo="${esc(o.titulo)}">`;
  }
  const tejuelo = (n, grande = false) => (n ? `<span class="tejuelo tejuelo--${esc(n)} ${grande ? "tejuelo--grande" : ""}" role="img" aria-label="Nivel de relevancia ${esc(n)}">${esc(n)}</span>` : "");
  const corazon = (o) => {
    const on = E.favs.has(o.id);
    return `<button class="corazon" type="button" data-fav="${o.id}" aria-pressed="${on}" aria-label="Guardar ${esc(o.titulo)} en favoritos">${ICONO.corazon}</button>`;
  };
  const meta = (o) => `<p class="meta"><span>${TIPO[o.tipo] || ""}</span>${o.anio ? `<span>${anios(o)}</span>` : ""}</p>`;
  const tarjeta = (o) => `
    <article class="tarjeta">
      <a class="tarjeta__imagen" href="#/obra/${o.id}" tabindex="-1" aria-hidden="true">${poster(o)}</a>
      ${tejuelo(o.relevancia)}
      ${corazon(o)}
      <h3 class="tarjeta__titulo"><a href="#/obra/${o.id}">${esc(o.titulo)}</a></h3>
      ${meta(o)}
    </article>`;
  const rejilla = (lista) => `<div class="rejilla">${lista.map(tarjeta).join("")}</div>`;
  const carrusel = (lista) => `<div class="carrusel">${lista.map(tarjeta).join("")}</div>`;

  function notaOcultas() {
    const n = ocultas();
    if (!E.evitar.size) return "";
    return `<p class="nota">Estás evitando ${E.evitar.size === 1 ? "1 aviso" : E.evitar.size + " avisos"}: ${n === 1 ? "hay 1 obra oculta" : "hay " + n + " obras ocultas"}. <button class="enlace-suave boton-texto" type="button" data-accion="abrir-evitar">Cambiar</button></p>`;
  }

  function toast(texto) {
    const t = $("#toast");
    t.textContent = texto;
    t.classList.add("visible");
    clearTimeout(toast.id);
    toast.id = setTimeout(() => t.classList.remove("visible"), 2200);
  }

  // ---------- Campaña para ampliar la base de datos ----------
  const hoyISO = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
  function campana() {
    const c = CFG.campana;
    if (!c || !CFG.formularioAltas || !seguro(CFG.formularioAltas)) return null;
    const hoy = hoyISO();
    if (hoy < c.desde || hoy > c.hasta) return null;
    const hechas = E.obras.filter((o) => o.publicada && o.publicada.slice(0, 10) >= c.desde).length;
    return { c, hechas, falta: Math.max(0, c.objetivo - hechas) };
  }
  function tarjetaCampana() {
    const k = campana();
    if (!k || E.campanaCerrada === k.c.id) return "";
    const logrado = k.hechas >= k.c.objetivo;
    const plural = (n) => (n === 1 ? "1 obra nueva" : `${n} obras nuevas`);
    return `
      <aside class="campana" aria-labelledby="campana-t">
        <img class="campana__img" src="${logrado ? "marca/buholira.svg" : "img/campana/cubo.webp"}" alt="" width="96" height="84" decoding="async">
        <div class="campana__texto">
          <h2 id="campana-t">${logrado ? "¡Objetivo conseguido!" : "Ayúdanos a descongelar la Safoteca"}</h2>
          <p>${logrado
            ? "Gracias a todas las que habéis aportado: la Safoteca ha crecido. Si conoces más series o películas, sigue proponiéndolas."
            : `Faltan ${plural(k.falta)} para llegar al objetivo. ¿Conoces una serie o película con representación lésbica o bisexual que no esté? Propónla.`}</p>
          <progress class="campana__barra" max="${k.c.objetivo}" value="${Math.min(k.hechas, k.c.objetivo)}" aria-label="Obras nuevas conseguidas"></progress>
          <p class="campana__cuenta">${Math.min(k.hechas, k.c.objetivo)} de ${k.c.objetivo} obras nuevas</p>
          <div class="acciones">
            <a class="boton" href="${esc(CFG.formularioAltas)}" target="_blank" rel="noopener noreferrer">Añadir una obra ${ICONO.fuera}</a>
            <button class="boton boton--claro" type="button" data-accion="cerrar-campana">Ahora no</button>
          </div>
        </div>
      </aside>`;
  }
  const enlaceAltas = (texto) => (CFG.formularioAltas && seguro(CFG.formularioAltas)
    ? `<a class="boton boton--claro" href="${esc(CFG.formularioAltas)}" target="_blank" rel="noopener noreferrer">${texto} ${ICONO.fuera}</a>` : "");

  // ---------- Vistas ----------
  function vistaInicio() {
    const v = visibles();
    if (!E.obras.length) return `<div class="vacio"><p>Todavía no hay obras publicadas.</p></div>`;
    const nov = [...v].filter((o) => o.anio).sort((a, b) => (b.anio_fin || b.anio) - (a.anio_fin || a.anio) || (b.publicada || "").localeCompare(a.publicada || "") || az(a, b)).slice(0, 10);
    const grupos = Array.isArray(CFG.portada) && CFG.portada.length ? CFG.portada : [{ tipo: "novedades" }];
    const seccion = (id, titulo, lista, href) => (lista.length ? `
      <section class="seccion" aria-labelledby="${id}">
        <div class="seccion__cabecera">
          <h2 class="seccion__titulo" id="${id}">${titulo}</h2>
          ${href ? `<a class="enlace-suave" href="${href}">Ver todo</a>` : ""}
        </div>${carrusel(lista)}
      </section>` : "");
    const intro = E.introVista ? "" : `
      <aside class="nota" aria-label="Cómo funcionan los avisos">
        <p><strong>Los avisos de contenido están ocultos</strong> para no destripar nada. Puedes verlos en cada ficha, mostrarlos siempre o elegir qué prefieres evitar: esas obras no aparecerán en ninguna lista.</p>
        <div class="acciones">
          <button class="boton" type="button" data-accion="abrir-evitar">Elegir qué evitar</button>
          <button class="boton boton--claro" type="button" data-accion="cerrar-intro">Entendido</button>
        </div>
      </aside>`;
    const buscador = `<form role="search" id="form-buscar-inicio" class="buscador-inicio"><label class="solo-lectores" for="buscar-inicio">Buscar por título o actriz</label>
      ${campoBuscar({ id: "buscar-inicio", valor: "", formulario: true })}</form>`;
    return `<h1 class="solo-lectores">La Safoteca</h1>${buscador}${intro}${tarjetaCampana()}${notaOcultas()}
      ${grupos.map((g, i) => (g.tipo === "novedades"
        ? seccion("s-novedades", "Novedades", nov, "#/catalogo?orden=recientes")
        : seccion("s-grupo-" + i, esc(g.titulo), (g.ids || []).map((id) => v.find((o) => o.id === id)).filter(Boolean), ""))).join("")}`;
  }

  // Campo de búsqueda con lupa (Inicio) o con una x para borrar el texto (catálogo).
  function campoBuscar({ id, valor, formulario }) {
    const boton = formulario
      ? `<button class="campo-buscar__boton" type="submit" aria-label="Buscar">${ICONO.lupa}</button>`
      : `<button class="campo-buscar__boton" type="button" data-accion="borrar-busqueda" aria-label="Borrar la búsqueda" ${valor ? "" : "hidden"}>${ICONO.cerrar}</button>`;
    return `<div class="campo-buscar"><input class="campo" id="${id}" type="search" placeholder="Buscar por título o actriz" value="${esc(valor)}" autocomplete="off" enterkeyhint="search">${boton}</div>`;
  }

  function vistaCatalogo(f) {
    const tipoChip = (valor, texto) => `<button class="chip" type="button" data-tipo="${valor}" aria-pressed="${f.tipo === valor}">${texto}</button>`;
    return `
      <h1 class="solo-lectores">Series y películas</h1>
      <div class="barra">
        <form role="search" id="form-buscar"><label class="solo-lectores" for="buscar">Buscar por título o actriz</label>
          ${campoBuscar({ id: "buscar", valor: f.q })}</form>
        <div class="barra__fila">
          <div class="chips" role="group" aria-label="Tipo">${tipoChip("", "Todo")}${tipoChip("serie", "Series")}${tipoChip("pelicula", "Películas")}</div>
          <label class="solo-lectores" for="ordenar">Ordenar por</label>
          <select class="campo campo--ordenar" id="ordenar">
            <option value="az">A–Z</option><option value="recientes">Más recientes</option><option value="relevancia">Nivel de relevancia</option>
          </select>
        </div>
        <p class="resumen" id="resumen" aria-live="polite"></p>
      </div>
      ${notaOcultas()}
      <div id="resultados"></div>`;
  }

  function pintarResultados() {
    const f = E.F;
    const lista = filtrar(f);
    const n = lista.length;
    $("#resumen").textContent = n === 1 ? "1 obra" : `${n} obras`;
    $("#resultados").innerHTML = n ? rejilla(lista) : `
      <div class="vacio"><p>No hay obras con estos filtros.</p>
        <div class="acciones" style="justify-content:center"><button class="boton" type="button" data-accion="quitar-filtros">${f.q ? "Quitar filtros y búsqueda" : "Quitar filtros"}</button></div>
        ${CFG.formularioAltas ? `<p style="margin:1.25rem 0 .5rem">¿No encuentras una serie o película? Propónla y la añadiremos.</p>${enlaceAltas("Añadir una obra")}` : ""}</div>`;
    $$('[data-tipo]').forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tipo === f.tipo)));
    $("#ordenar").value = f.orden;
    ajustarCabecera();
  }

  function sincronizar() {
    const qs = paramsDe(E.F);
    history.replaceState(null, "", "#/catalogo" + (qs ? "?" + qs : ""));
    if (rutaActual().ruta === "/catalogo") pintarResultados();
  }

  function vistaFavoritos() {
    const lista = visibles().filter((o) => E.favs.has(o.id)).sort(az);
    if (!lista.length) {
      return `<h1 class="solo-lectores">Favoritos</h1><div class="vacio"><p>Aún no has guardado nada. Toca el corazón de una ficha para verla aquí.</p>
        <a class="boton" href="#/catalogo">Explorar series y películas</a></div>
        <p class="resumen">Tus favoritos se guardan solo en este dispositivo.</p>`;
    }
    return `<h1 class="solo-lectores">Favoritos</h1>${notaOcultas()}
      <p class="resumen" style="margin-bottom:1rem">${lista.length === 1 ? "1 obra guardada" : lista.length + " obras guardadas"} en este dispositivo.</p>${rejilla(lista)}`;
  }

  function vistaObra(id) {
    const o = E.porId.get(id);
    if (!o) return `<h1 class="solo-lectores">Ficha no encontrada</h1><div class="vacio"><p>No hemos encontrado esta ficha.</p><a class="boton" href="#/catalogo">Ver el catálogo</a></div>`;
    const rep = CFG.reporteEnlaces;
    const urlReporte = (x) => {
      const q = new URLSearchParams({ usp: "pp_url" });
      q.set(rep.campos.id, String(o.id)); q.set(rep.campos.obra, o.titulo); q.set(rep.campos.plataforma, x.n); q.set(rep.campos.enlace, x.u);
      return `${rep.url}?${q}`;
    };
    const lugares = (o.plataformas || o.donde_ver.map((u) => ({ n: nombreSitio(u), p: "INT", u }))).filter((x) => seguro(x.u)).map((x) => {
      const pais = x.p === "INT" ? "" : PAIS[x.p] || x.p;
      const enlace = `<a class="boton boton--claro" href="${esc(x.u)}" target="_blank" rel="noopener noreferrer">${esc(x.n)}${pais ? ` <span class="boton__pais${x.p === "ES" ? "" : " boton__pais--fuera"}">${esc(pais)}</span>` : ""} ${ICONO.fuera}</a>`;
      if (!(rep && rep.url && rep.campos)) return enlace;
      return `<span class="enlace-item">${enlace}<a class="reportar" href="${esc(urlReporte(x))}" target="_blank" rel="noopener noreferrer" title="Avisar de que este enlace no funciona" aria-label="Avisar de que el enlace de ${esc(x.n)} no funciona">${ICONO.bandera}</a></span>`;
    }).join("");
    const hayFuera = (o.plataformas || []).some((x) => !delPais(x));
    const letterboxd = o.letterboxd && seguro(o.letterboxd)
      ? `<a class="boton boton--claro" href="${esc(o.letterboxd)}" target="_blank" rel="noopener noreferrer">Ver en Letterboxd ${ICONO.fuera}</a>` : "";
    const info = o.info.filter(seguro).map((u) => `<a class="chip" href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(host(u))}</a>`).join("");
    const nombres = o.avisos.map((a) => a.nombre);
    const evitados = nombres.filter((n) => E.evitar.has(claveAviso(n)));
    const chipLista = (clave, valores) => valores.map((v) => `<a class="chip" href="#/catalogo?${clave}=${encodeURIComponent(v)}">${esc(v)}</a>`).join("");

    const final = o.final_feliz === true ? "Final feliz" : o.final_feliz === false ? "Final no feliz" : "";
    const totalAvisos = nombres.length + (final ? 1 : 0);
    let avisos = `<section class="bloque bloque--avisos" aria-labelledby="t-avisos"><h2 id="t-avisos">Avisos de contenido</h2>`;
    if (!totalAvisos) {
      avisos += `<p>No hay avisos registrados para esta obra.</p>`;
    } else {
      if (evitados.length) avisos += `<p class="nota nota--alerta">Incluye ${evitados.length > 1 ? "avisos que has elegido evitar" : "un aviso que has elegido evitar"}: ${evitados.map(esc).join(", ")}.</p>`;
      avisos += `<p id="avisos-resumen" ${E.verAvisos ? "hidden" : ""}>Esta ficha tiene ${totalAvisos === 1 ? "1 aviso" : totalAvisos + " avisos"}. Están ocultos para no destripar la historia.</p>
        <div id="avisos-contenido" ${E.verAvisos ? "" : "hidden"}><ul class="lista-avisos">${final ? `<li class="aviso-final">${final}</li>` : ""}${nombres.map((n) => `<li>${esc(n)}</li>`).join("")}</ul></div>
        <p style="margin-top:.75rem"><button class="boton boton--claro" type="button" data-accion="alternar-avisos" aria-expanded="${E.verAvisos}" aria-controls="avisos-contenido">${E.verAvisos ? "Ocultar los avisos" : "Ver los avisos"}</button></p>`;
    }
    avisos += `</section>`;

    const dato = (k, v) => (v ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : "");
    const explica = CFG.textoRelevancia && CFG.textoRelevancia[o.relevancia]
      ? `<details class="explica"><summary>¿Qué significa el nivel ${esc(o.relevancia)}?</summary><p>${esc(CFG.textoRelevancia[o.relevancia])}</p></details>` : "";
    const disp = o.disponible_espana === null ? "" : o.disponible_espana ? "Sí" : "No";

    return `
      <article class="ficha">
        <div class="ficha__portada">${poster(o, true)}${corazon(o)}</div>
        <div class="ficha__resto">
          <header>
            <h1 class="ficha__titulo">${esc(o.titulo)}</h1>
            ${o.titulo_original && o.titulo_original !== o.titulo ? `<p class="ficha__original">${esc(o.titulo_original)}</p>` : ""}
            <div class="ficha__datos">
              ${tejuelo(o.relevancia, true)}
              <span>${TIPO[o.tipo] || ""}${o.anio ? " " + anios(o) : ""}</span>
              ${o.edad != null ? `<span class="edad" title="Edad recomendada">${esc(textoEdad(o))}</span>` : ""}
            </div>
            ${explica}
          </header>
          ${avisos}
          ${o.sinopsis ? `<section class="bloque"><h2>Sinopsis</h2><p>${esc(o.sinopsis)}</p></section>` : ""}
          ${lugares ? `<section class="bloque"><h2>Dónde ver</h2><div class="enlaces">${lugares}</div>${hayFuera ? '<p class="resumen" style="margin-top:.5rem">Los enlaces marcados con otro país pueden no estar disponibles en España.</p>' : ""}${rep && rep.url ? '<p class="resumen" style="margin-top:.5rem">¿Un enlace no funciona? Toca la bandera junto a él para avisarnos.</p>' : ""}</section>` : ""}
          ${o.generos.length || o.tematicas.length ? `<section class="bloque"><h2>Explorar</h2>
            ${o.generos.length ? `<h3>Géneros</h3><div class="chips">${chipLista("gen", o.generos)}</div>` : ""}
            ${o.tematicas.length ? `<h3>Temáticas</h3><div class="chips">${chipLista("tem", o.tematicas)}</div>` : ""}</section>` : ""}
          <section class="bloque"><h2>Datos</h2><dl class="dato">
            ${dato("País", o.pais)}${dato("Temporadas", o.temporadas)}${dato("En España", disp)}
            ${dato("Reparto", o.actrices.join(", "))}${dato("Dirección", o.directores.join(", "))}
          </dl></section>
          ${info || letterboxd ? `<section class="bloque"><h2>Más información</h2>${letterboxd ? `<div class="enlaces">${letterboxd}</div>` : ""}${info ? `<div class="chips">${info}</div>` : ""}</section>` : ""}
        </div>
      </article>`;
  }

  function vistaAjustes() {
    const n = E.evitar.size;
    const fecha = E.meta.generado ? new Date(E.meta.generado).toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" }) : "";
    return `
      <h1 class="solo-lectores">Ajustes</h1>
      <div class="ajustes">
        <section class="bloque" aria-labelledby="a1"><h2 id="a1">Avisos de contenido</h2>
          <label class="interruptor"><input type="checkbox" id="sw-avisos" role="switch" ${E.verAvisos ? "checked" : ""}>
            <span class="interruptor__pista" aria-hidden="true"></span>
            <span>Mostrar los avisos en las fichas<small>Si lo dejas apagado, cada ficha te pregunta antes de enseñarlos.</small></span></label>
        </section>
        <section class="bloque" aria-labelledby="a2"><h2 id="a2">Qué prefiero evitar</h2>
          <p style="margin-bottom:.75rem">Elige los avisos que no quieres encontrarte. Las obras que los tienen desaparecen de todas las listas, sin decirte cuáles son.</p>
          <p class="resumen" style="margin-bottom:.75rem">${n ? (n === 1 ? "Estás evitando 1 aviso." : `Estás evitando ${n} avisos.`) : "Ahora mismo no evitas ningún aviso."}</p>
          <button class="boton" type="button" data-accion="abrir-evitar">Elegir avisos a evitar</button>
        </section>
        ${CFG.formularioAltas ? `<section class="bloque" aria-labelledby="a5"><h2 id="a5">Ayúdanos a crecer</h2>
          <p style="margin-bottom:.75rem">¿Falta alguna serie o película con representación lésbica o bisexual? Propónla con un formulario y la revisaremos.</p>
          ${enlaceAltas("Añadir una obra")}</section>` : ""}
        <section class="bloque" aria-labelledby="a3"><h2 id="a3">Tus datos</h2>
          <p style="margin-bottom:.75rem">Favoritos y preferencias se guardan solo en este dispositivo. No tenemos cuentas ni servidores que los reciban.</p>
          <button class="boton boton--claro" type="button" data-accion="borrar-datos">Borrar favoritos y preferencias</button>
        </section>
        <section class="bloque" aria-labelledby="a4"><h2 id="a4">Sobre ${esc(CFG.nombre || "La Safoteca")}</h2>
          <p>${esc(CFG.lema || "")}</p>
          ${E.meta.total ? `<p class="resumen" style="margin-top:.5rem">${E.meta.total} obras${fecha ? ", datos del " + fecha : ""}.</p>` : ""}
          ${CFG.contacto ? `<p style="margin-top:.75rem"><a class="enlace-suave" href="${esc(CFG.contacto)}">Enviar una sugerencia</a></p>` : ""}
        </section>
      </div>`;
  }

  // ---------- Hoja de filtros y avisos a evitar ----------
  const hoja = () => $("#hoja");

  function gruposAvisos() {
    const g = new Map(); // clave -> { etiquetas: Map(nombre -> nº de obras), obras: Set(id) }
    E.obras.forEach((o) => o.avisos.forEach((a) => {
      const k = claveAviso(a.nombre);
      if (!g.has(k)) g.set(k, { etiquetas: new Map(), obras: new Set() });
      const x = g.get(k);
      x.etiquetas.set(a.nombre, (x.etiquetas.get(a.nombre) || 0) + 1);
      x.obras.add(o.id);
    }));
    return [...g].map(([k, x]) => ({
      clave: k, obras: x.obras.size,
      etiqueta: [...x.etiquetas].sort((p, q) => q[1] - p[1] || q[0].length - p[0].length)[0][0],
    })).sort((p, q) => norm(p.etiqueta).localeCompare(norm(q.etiqueta), "es"));
  }
  function listaAvisos(consulta) {
    const q = norm(consulta).trim();
    const todos = gruposAvisos();
    const fila = (g) => `<label class="marca"><input type="checkbox" data-evitar="${esc(g.clave)}" ${E.evitar.has(g.clave) ? "checked" : ""}><span>${esc(g.etiqueta)}</span><span>${g.obras}</span></label>`;
    const marcados = todos.filter((g) => E.evitar.has(g.clave));
    let resto = todos.filter((g) => !E.evitar.has(g.clave) && (!q || norm(g.etiqueta).includes(q)));
    resto.sort((p, r) => r.obras - p.obras || norm(p.etiqueta).localeCompare(norm(r.etiqueta), "es"));
    const total = resto.length;
    if (!q) resto = resto.slice(0, 12);
    let html = "";
    if (marcados.length) {
      html += `<div class="lista-marcas__titulo"><span>Estás evitando (${marcados.length})</span><button class="boton-texto enlace-suave" type="button" data-accion="quitar-evitar">Quitar todos</button></div>${marcados.map(fila).join("")}`;
    }
    if (resto.length) html += `<p class="lista-marcas__titulo">${q ? "Resultados" : "Los más habituales"}</p>${resto.map(fila).join("")}`;
    else if (!marcados.length) html += `<p class="resumen">No hay avisos con ese nombre.</p>`;
    else if (q) html += `<p class="resumen">No hay más avisos con ese nombre.</p>`;
    if (!q && total > resto.length) html += `<p class="resumen">Escribe para buscar entre los ${todos.length} avisos.</p>`;
    return html;
  }
  function chipsTematica(consulta) {
    const q = norm(consulta).trim();
    const sel = E.F.tem;
    const frecuencia = new Map();
    E.obras.forEach((o) => o.tematicas.forEach((t) => frecuencia.set(t, (frecuencia.get(t) || 0) + 1)));
    let lista = E.cat.tematicas.filter((t) => !sel.includes(t) && (!q || norm(t).includes(q)));
    lista.sort((a, b) => (frecuencia.get(b) || 0) - (frecuencia.get(a) || 0) || norm(a).localeCompare(norm(b), "es"));
    const total = lista.length;
    lista = lista.slice(0, q ? 40 : 16);
    return [...sel, ...lista].map((t) => `<button class="chip" type="button" data-tem="${esc(t)}" aria-pressed="${sel.includes(t)}">${esc(t)}</button>`).join("")
      + (total > lista.length ? `<p class="resumen" style="flex-basis:100%">Escribe para buscar entre ${E.cat.tematicas.length} temáticas.</p>` : "");
  }

  function chipsPlataforma() {
    const f = E.F;
    const cuenta = new Map();
    visibles().forEach((o) => {
      const claves = new Set((o.plataformas || []).filter((x) => f.otros || delPais(x)).map(clavePlat));
      claves.forEach((k) => cuenta.set(k, (cuenta.get(k) || 0) + 1));
    });
    f.plat.forEach((k) => { if (!cuenta.has(k)) cuenta.set(k, 0); });
    const lista = [...cuenta].sort((a, b) => (a[0] === "Otras") - (b[0] === "Otras") || b[1] - a[1] || a[0].localeCompare(b[0], "es"));
    return lista.map(([k, n]) => `<button class="chip" type="button" data-plat="${esc(k)}" aria-pressed="${f.plat.includes(k)}">${esc(k)} <span class="chip__n">${n}</span></button>`).join("");
  }

  function abrirHoja(modo) {
    const h = hoja();
    const soloEvitar = modo === "evitar";
    const f = E.F || filtrosDe(new URLSearchParams());
    const grupoEvitar = `
      <section class="grupo" id="grupo-evitar" aria-labelledby="${soloEvitar ? "hoja-titulo" : "g-evitar"}">
        ${soloEvitar ? "" : '<h3 id="g-evitar">Qué prefiero evitar</h3>'}
        <p>Las obras con estos avisos no aparecerán en ninguna lista. No se muestra cuáles son.</p>
        <label class="solo-lectores" for="buscar-aviso">Buscar un aviso</label>
        <input class="campo" id="buscar-aviso" type="search" placeholder="Buscar un aviso" autocomplete="off">
        <div class="lista-marcas" id="lista-avisos">${listaAvisos("")}</div>
      </section>`;
    const grupoFiltros = soloEvitar ? "" : `
      <section class="grupo" aria-labelledby="g-rel"><h3 id="g-rel">Nivel de relevancia</h3>
        <div class="chips">${["A", "B", "C"].map((n) => `<button class="chip chip--tejuelo" type="button" data-rel="${n}" aria-pressed="${f.rel.includes(n)}" aria-label="Nivel ${n}">${n}</button>`).join("")}</div></section>
      <section class="grupo" aria-labelledby="g-final"><h3 id="g-final">Final de la historia</h3>
        <label class="interruptor"><input type="checkbox" id="sw-final" role="switch" ${f.final ? "checked" : ""}>
          <span class="interruptor__pista" aria-hidden="true"></span>
          <span>Solo con final feliz<small>Salen solo las obras con final feliz confirmado.</small></span></label></section>
      <section class="grupo" aria-labelledby="g-gen"><h3 id="g-gen">Género</h3>
        <div class="chips">${E.cat.generos.map((g) => `<button class="chip" type="button" data-gen="${esc(g)}" aria-pressed="${f.gen.includes(g)}">${esc(g)}</button>`).join("")}</div></section>
      <section class="grupo" aria-labelledby="g-tem"><h3 id="g-tem">Temática</h3>
        <label class="solo-lectores" for="buscar-tem">Buscar una temática</label>
        <input class="campo" id="buscar-tem" type="search" placeholder="Buscar una temática" autocomplete="off" style="margin-bottom:.6rem">
        <div class="chips" id="chips-tem">${chipsTematica("")}</div></section>
      <section class="grupo" aria-labelledby="g-plat"><h3 id="g-plat">Plataforma</h3>
        <div class="chips" id="chips-plat">${chipsPlataforma()}</div>
        <label class="marca" style="margin-top:.6rem"><input type="checkbox" data-otros ${f.otros ? "checked" : ""}><span>Incluir plataformas de otros países</span></label>
        <p class="resumen" style="margin-top:.4rem">Por defecto solo salen las de España y las que no dependen de un país. «Otras» agrupa webs no oficiales.</p></section>
      <section class="grupo" aria-labelledby="g-edad"><h3 id="g-edad">Edad recomendada</h3>
        <label class="solo-lectores" for="sel-edad">Edad máxima</label>
        <select class="campo" id="sel-edad">
          <option value="">Cualquiera</option><option value="0">Todos los públicos</option><option value="7">Hasta 7 años</option>
          <option value="12">Hasta 12 años</option><option value="14">Hasta 14 años</option><option value="16">Hasta 16 años</option>
        </select>
        <p class="resumen" style="margin-top:.5rem">Las obras sin edad indicada se muestran siempre.</p></section>`;
    h.innerHTML = `
      <div class="hoja__cabecera"><h2 id="hoja-titulo">${soloEvitar ? "Qué prefiero evitar" : "Filtros"}</h2>
        <button class="boton boton--claro" type="button" data-accion="cerrar-hoja">Cerrar</button></div>
      <div class="hoja__cuerpo">${grupoFiltros}${grupoEvitar}</div>
      <div class="hoja__pie">
        <button class="boton" type="button" data-accion="cerrar-hoja" id="hoja-ver">${soloEvitar ? "Listo" : ""}</button>
        ${soloEvitar ? "" : '<button class="boton boton--claro" type="button" data-accion="quitar-filtros">Quitar filtros</button>'}
      </div>`;
    if (!soloEvitar) $("#sel-edad", h).value = f.edad;
    h.dataset.modo = modo;
    actualizarPieHoja();
    if (!h.open) h.showModal();
    if (modo === "evitar") { const g = $("#buscar-aviso", h); g && g.focus({ preventScroll: true }); }
  }

  function actualizarPieHoja() {
    const h = hoja();
    if (h.dataset.modo === "evitar") return;
    const n = filtrar(E.F).length;
    $("#hoja-ver", h).textContent = n === 1 ? "Ver 1 obra" : `Ver ${n} obras`;
  }

  function alternar(arr, v) {
    const i = arr.indexOf(v);
    if (i >= 0) arr.splice(i, 1); else arr.push(v);
    return i < 0;
  }

  // ---------- Enrutado ----------
  function rutaActual() {
    const h = location.hash.slice(1) || "/";
    const [ruta, qs = ""] = h.split("?");
    return { ruta, p: new URLSearchParams(qs) };
  }

  function ajustarCabecera() {
    const { ruta } = rutaActual();
    const izq = $("#btn-izq");
    const filtros = $("#btn-filtros");
    const raiz = ["/", "/catalogo", "/favoritos"].includes(ruta);
    izq.innerHTML = raiz ? ICONO.menu : ICONO.atras;
    izq.setAttribute("aria-label", raiz ? "Ajustes" : "Volver");
    const hayFiltros = ruta === "/" || ruta === "/catalogo";
    filtros.hidden = !hayFiltros;
    if (hayFiltros) {
      const n = (ruta === "/catalogo" && E.F ? activos(E.F) : 0) + (E.evitar.size ? 1 : 0);
      filtros.innerHTML = ICONO.filtro + (n ? `<span class="insignia" aria-hidden="true">${n}</span>` : "");
      filtros.setAttribute("aria-label", n ? `Filtros y avisos a evitar, ${n} activos` : "Filtros y avisos a evitar");
    }
  }

  function pintarTabs(ruta) {
    const t = (href, activa, icono, texto) => `<a class="tabs__enlace" href="${href}" ${activa ? 'aria-current="page"' : ""}><span class="tabs__icono">${icono}</span>${texto}</a>`;
    $("#tabs").innerHTML = t("#/", ruta === "/", ICONO.inicio, "Inicio")
      + t("#/catalogo", ruta === "/catalogo", ICONO.claqueta, "Series y películas")
      + t("#/favoritos", ruta === "/favoritos", ICONO.corazon.replace("<svg ", '<svg fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" '), "Favoritos");
  }

  function pintar(arriba = true) {
    const { ruta, p } = rutaActual();
    const vista = $("#vista");
    let titulo = CFG.nombre || "La Safoteca";
    let doc = titulo;
    if (ruta === "/catalogo") {
      E.F = filtrosDe(p);
      vista.innerHTML = vistaCatalogo(E.F);
      titulo = "Series y películas"; doc = titulo + " · " + doc;
      pintarResultados();
      if (E.abrirAlCargar) { const m = E.abrirAlCargar; E.abrirAlCargar = null; abrirHoja(m); }
    } else if (ruta === "/favoritos") {
      vista.innerHTML = vistaFavoritos(); titulo = "Favoritos"; doc = titulo + " · " + doc;
    } else if (ruta === "/ajustes") {
      vista.innerHTML = vistaAjustes(); titulo = "Ajustes"; doc = titulo + " · " + doc;
    } else if (ruta.startsWith("/obra/")) {
      const id = parseInt(ruta.split("/")[2], 10);
      vista.innerHTML = vistaObra(id);
      const o = E.porId.get(id);
      titulo = o ? o.titulo : "Ficha"; doc = titulo + " · " + doc;
    } else {
      vista.innerHTML = vistaInicio();
    }
    const tit = $("#titulo-vista");
    const pag = $("#titulo-pagina");
    if (["/", "/catalogo", "/favoritos"].includes(ruta)) {
      // En las pestañas principales se muestra siempre el logotipo (claro u oscuro según el tema);
      // en el inicio el h1 accesible ya existe en la vista, y en las otras dos el nombre de la pestaña
      // va a la derecha, antes del icono de filtros.
      tit.innerHTML = '<img class="cabecera__logo cabecera__logo--claro" src="marca/logo-horizontal.svg" alt="La Safoteca">'
        + '<img class="cabecera__logo cabecera__logo--oscuro" src="marca/logo-horizontal-oscuro.svg" alt="" aria-hidden="true">';
      pag.hidden = ruta === "/";
      pag.textContent = ruta === "/" ? "" : titulo;
    } else {
      tit.textContent = ruta.startsWith("/obra/") ? "" : titulo;
      pag.hidden = true; pag.textContent = "";
    }
    document.title = doc;
    pintarTabs(ruta);
    ajustarCabecera();
    pintarFlotante();
    if (arriba) { window.scrollTo(0, 0); vista.focus({ preventScroll: true }); }
  }

  // ---------- Eventos ----------
  document.addEventListener("click", (e) => {
    const fav = e.target.closest("[data-fav]");
    if (fav) {
      const id = Number(fav.dataset.fav);
      const on = !E.favs.has(id);
      if (on) E.favs.add(id); else E.favs.delete(id);
      guardar.escribir("favs", [...E.favs]);
      $$(`[data-fav="${id}"]`).forEach((b) => b.setAttribute("aria-pressed", String(on)));
      toast(on ? "Guardado en favoritos" : "Quitado de favoritos");
      if (rutaActual().ruta === "/favoritos" && !on) { const y = scrollY; pintar(false); scrollTo(0, y); }
      return;
    }
    const tipo = e.target.closest("[data-tipo]");
    if (tipo && E.F) { E.F.tipo = tipo.dataset.tipo; sincronizar(); if (hoja().open) actualizarPieHoja(); return; }

    const rel = e.target.closest("[data-rel]");
    if (rel) { alternar(E.F.rel, rel.dataset.rel); rel.setAttribute("aria-pressed", String(E.F.rel.includes(rel.dataset.rel))); sincronizar(); actualizarPieHoja(); return; }
    const gen = e.target.closest("[data-gen]");
    if (gen) { alternar(E.F.gen, gen.dataset.gen); gen.setAttribute("aria-pressed", String(E.F.gen.includes(gen.dataset.gen))); sincronizar(); actualizarPieHoja(); return; }
    const otros = e.target.closest("[data-otros]");
    if (otros) {
      E.F.otros = otros.checked;
      if (!otros.checked) E.F.plat = E.F.plat.filter((k) => !k.includes(" · "));
      sincronizar(); $("#chips-plat").innerHTML = chipsPlataforma(); actualizarPieHoja(); return;
    }
    const plat = e.target.closest("[data-plat]");
    if (plat) { alternar(E.F.plat, plat.dataset.plat); sincronizar(); $("#chips-plat").innerHTML = chipsPlataforma(); actualizarPieHoja(); return; }
    const tem = e.target.closest("[data-tem]");
    if (tem) { alternar(E.F.tem, tem.dataset.tem); sincronizar(); $("#chips-tem").innerHTML = chipsTematica($("#buscar-tem").value); actualizarPieHoja(); return; }

    const acc = e.target.closest("[data-accion]");
    if (acc) {
      switch (acc.dataset.accion) {
        case "borrar-busqueda": {
          clearTimeout(espera); E.F.q = ""; limpiarCampoBusqueda(); sincronizar();
          const b = $("#buscar"); b && b.focus({ preventScroll: true });
          break;
        }
        case "quitar-evitar": {
          E.evitar.clear(); guardar.escribir("evitar", []); E.evitarCambiado = true;
          const campo = $("#buscar-aviso"); $("#lista-avisos").innerHTML = listaAvisos(campo ? campo.value : "");
          break;
        }
        case "abrir-evitar": abrirHoja("evitar"); break;
        case "cerrar-hoja": hoja().close(); break;
        case "cerrar-campana": { const k = campana(); if (k) { E.campanaCerrada = k.c.id; guardar.escribir("campana", k.c.id); } pintar(false); break; }
        case "cerrar-intro": E.introVista = true; guardar.escribir("intro", true); pintar(false); break;
        case "quitar-filtros":
          clearTimeout(espera);
          E.F = filtrosDe(new URLSearchParams()); sincronizar();
          limpiarCampoBusqueda();
          if (hoja().open) abrirHoja("filtros");
          break;
        case "alternar-avisos": {
          const caja = $("#avisos-contenido"); const resumen = $("#avisos-resumen");
          const mostrar = caja.hidden;
          caja.hidden = !mostrar; resumen.hidden = mostrar;
          acc.setAttribute("aria-expanded", String(mostrar));
          acc.textContent = mostrar ? "Ocultar los avisos" : "Ver los avisos";
          break;
        }
        case "borrar-datos":
          if (acc.dataset.seguro) {
            guardar.borrar(); E.favs.clear(); E.evitar.clear(); E.verAvisos = false; E.introVista = false;
            pintar(false); toast("Datos borrados de este dispositivo");
          } else {
            acc.dataset.seguro = "1"; acc.textContent = "Pulsa otra vez para borrar";
            setTimeout(() => { if (acc.isConnected) { delete acc.dataset.seguro; acc.textContent = "Borrar favoritos y preferencias"; } }, 4000);
          }
          break;
      }
      return;
    }
    if (e.target === hoja()) hoja().close(); // clic fuera de la hoja
  });

  document.addEventListener("change", (e) => {
    const t = e.target;
    if (t.matches("[data-evitar]")) {
      if (t.checked) E.evitar.add(t.dataset.evitar); else E.evitar.delete(t.dataset.evitar);
      guardar.escribir("evitar", [...E.evitar]);
      E.evitarCambiado = true;
      if (E.F && rutaActual().ruta === "/catalogo") pintarResultados();
      actualizarPieHoja(); ajustarCabecera();
    } else if (t.id === "sel-edad") { E.F.edad = t.value; sincronizar(); actualizarPieHoja(); }
    else if (t.id === "ordenar") { E.F.orden = t.value; sincronizar(); }
    else if (t.id === "sw-final" && E.F) { E.F.final = t.checked ? "si" : ""; sincronizar(); actualizarPieHoja(); }
    else if (t.id === "sw-avisos") { E.verAvisos = t.checked; guardar.escribir("verAvisos", t.checked); }
  });

  let espera;
  const mostrarBorrar = (campo) => { const b = campo.parentElement.querySelector('[data-accion="borrar-busqueda"]'); if (b) b.hidden = !campo.value; };
  function limpiarCampoBusqueda() { const c = $("#buscar"); if (c) { c.value = ""; mostrarBorrar(c); } }
  document.addEventListener("input", (e) => {
    const t = e.target;
    if (t.id === "buscar") { mostrarBorrar(t); clearTimeout(espera); espera = setTimeout(() => { E.F.q = t.value.trim(); sincronizar(); }, 150); }
    else if (t.id === "buscar-aviso") $("#lista-avisos").innerHTML = listaAvisos(t.value);
    else if (t.id === "buscar-tem") $("#chips-tem").innerHTML = chipsTematica(t.value);
  });
  document.addEventListener("submit", (e) => {
    if (e.target.id === "form-buscar") { e.preventDefault(); document.activeElement.blur(); }
    else if (e.target.id === "form-buscar-inicio") {
      e.preventDefault();
      const q = $("#buscar-inicio").value.trim();
      document.activeElement.blur();
      location.hash = "#/catalogo" + (q ? "?q=" + encodeURIComponent(q) : "");
    }
  });

  // Si una imagen no carga, se muestra el hueco con el título.
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (img.tagName === "IMG" && img.classList.contains("poster")) {
      const d = document.createElement("div");
      d.className = "poster poster--vacio";
      d.style.setProperty("--tono", img.dataset.tono || "270");
      d.innerHTML = `<span>${esc(img.dataset.titulo || "")}</span>`;
      img.replaceWith(d);
    }
  }, true);

  $("#btn-izq").addEventListener("click", () => {
    const { ruta } = rutaActual();
    if (["/", "/catalogo", "/favoritos"].includes(ruta)) location.hash = "#/ajustes";
    else if (E.navegado) history.back();
    else location.hash = "#/catalogo";
  });
  $("#btn-filtros").addEventListener("click", () => {
    if (rutaActual().ruta === "/catalogo") abrirHoja("filtros");
    else { E.abrirAlCargar = "filtros"; location.hash = "#/catalogo"; }
  });
  hoja().addEventListener("close", () => {
    if (E.evitarCambiado) { E.evitarCambiado = false; const y = scrollY; pintar(false); scrollTo(0, y); }
    else ajustarCabecera();
  });
  window.addEventListener("hashchange", () => { if (!E.cargado) return; E.navegado = true; if (hoja().open) hoja().close(); pintar(true); });


  // ---------- UAT: buscador flotante (solo en la versión de pruebas) ----------
  const RAIZ_TABS = ["/", "/catalogo", "/favoritos"];
  function pintarFlotante() {
    const { ruta, p } = rutaActual();
    let f = $("#flotante");
    if (!RAIZ_TABS.includes(ruta)) { if (f) f.hidden = true; return; }
    if (!f) {
      f = document.createElement("div");
      f.id = "flotante"; f.className = "flotante";
      f.innerHTML = `<form role="search" id="form-flotante" class="flotante__panel" hidden>
          <label class="solo-lectores" for="buscar-flotante">Buscar por título o actriz</label>
          <input class="campo" id="buscar-flotante" type="search" placeholder="Buscar por título o actriz" autocomplete="off" enterkeyhint="search">
        </form>
        <button class="flotante__boton" id="btn-flotante" type="button" aria-label="Buscar" aria-expanded="false">${ICONO.lupa}</button>`;
      document.body.appendChild(f);
    }
    f.hidden = false; f.classList.remove("flotante--oculto");
    const campo = $("#buscar-flotante");
    campo.value = ruta === "/catalogo" ? (p.get("q") || "") : "";
  }
  function abrirFlotante(abrir) {
    const panel = $("#form-flotante"), btn = $("#btn-flotante");
    panel.hidden = !abrir; btn.setAttribute("aria-expanded", String(abrir));
    btn.innerHTML = abrir ? ICONO.cerrar : ICONO.lupa;
    btn.setAttribute("aria-label", abrir ? "Cerrar búsqueda" : "Buscar");
    if (abrir) $("#buscar-flotante").focus();
  }
  document.addEventListener("click", (e) => {
    if (e.target.closest("#btn-flotante")) abrirFlotante($("#form-flotante").hidden);
  });
  document.addEventListener("input", (e) => {
    if (e.target.id !== "buscar-flotante" || rutaActual().ruta !== "/catalogo") return;
    const c = $("#buscar");
    if (c) { c.value = e.target.value; c.dispatchEvent(new Event("input", { bubbles: true })); }
  });
  document.addEventListener("submit", (e) => {
    if (e.target.id !== "form-flotante") return;
    e.preventDefault();
    const q = $("#buscar-flotante").value.trim();
    document.activeElement.blur();
    abrirFlotante(false);
    if (rutaActual().ruta !== "/catalogo") { location.hash = "#/catalogo" + (q ? "?q=" + encodeURIComponent(q) : ""); }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && $("#form-flotante") && !$("#form-flotante").hidden) { abrirFlotante(false); $("#btn-flotante").focus(); } });
  let yPrev = 0;
  window.addEventListener("scroll", () => {
    const f = $("#flotante"); if (!f || f.hidden || !$("#form-flotante").hidden) return;
    const y = scrollY;
    if (y > yPrev + 8 && y > 120) f.classList.add("flotante--oculto");
    else if (y < yPrev - 8) f.classList.remove("flotante--oculto");
    yPrev = y;
  }, { passive: true });

  // ---------- Arranque ----------
  async function cargar() {
    try {
      const [a, b] = await Promise.all([fetch("data/obras.json"), fetch("data/catalogos.json")]);
      if (!a.ok || !b.ok) throw new Error("respuesta no válida");
      const datos = await a.json();
      E.cat = await b.json();
      E.meta = datos.meta || {};
      E.obras = datos.obras.map((o) => ({
        ...o,
        _h: norm([o.titulo, o.titulo_original, o.titulo_latam, ...o.actrices, ...o.directores].filter(Boolean).join(" ")),
      }));
      E.porId = new Map(E.obras.map((o) => [o.id, o]));
      E.cargado = true;
      pintar(false);
    } catch {
      $("#vista").innerHTML = `<div class="vacio"><p>No hemos podido cargar el catálogo. Comprueba tu conexión e inténtalo de nuevo.</p>
        <button class="boton" type="button" id="reintentar">Reintentar</button></div>`;
      $("#reintentar").addEventListener("click", () => { $("#vista").innerHTML = '<p class="cargando">Cargando el catálogo…</p>'; cargar(); });
    }
  }

  pintarTabs(rutaActual().ruta);
  ajustarCabecera();
  cargar();

  if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
    window.addEventListener("load", () => navigator.serviceWorker.register("./sw.js").catch(() => { /* sin modo sin conexión */ }));
  }
})();
