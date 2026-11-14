/* La Safoteca · «Proponer una obra» (#/proponer)
   Se carga solo al abrir esa pantalla. Entrada con Google, relleno automático desde TMDB (a través del
   servicio de Apps Script, que guarda la clave) y selectores de etiquetas con sugerencias.
   Las propuestas acaban como una fila más de la hoja de respuestas del formulario. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const norm = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

  let CFG = {}, LISTAS = null, OBRAS = [], credencial = null, tmdbId = "", ctxCuenta = "";
  const elegidas = { tematicas: new Set(), avisos: new Set(), generos: new Set() };

  const servicio = () => (CFG.proponer && CFG.proponer.servicio) || "";
  const clientId = () => (CFG.proponer && CFG.proponer.clientId) || "";

  // ---------- llamadas al servicio ----------
  async function pedir(params) {
    const u = new URL(servicio()); Object.entries(params).forEach(([k, v]) => u.searchParams.set(k, v));
    const r = await fetch(u, { redirect: "follow" });
    if (!r.ok) throw new Error("El buscador no responde (" + r.status + ")");
    const d = await r.json(); if (d.error) throw new Error(d.error); return d;
  }

  // ---------- selector de etiquetas: caja con sugerencias + «ver todas» plegado ----------
  function selector(clave, titulo, opciones, ayuda, otroCampo) {
    return `<section class="prop-grupo" data-sel="${clave}">
      <label class="prop-etq" for="sel-${clave}">${esc(titulo)}</label>
      ${ayuda ? `<p class="prop-ayuda">${esc(ayuda)}</p>` : ""}
      <div class="sel__elegidas" aria-live="polite"></div>
      <div class="sel__caja">
        <input id="sel-${clave}" type="text" autocomplete="off" placeholder="Escribe para buscar…" role="combobox" aria-expanded="false" aria-controls="sug-${clave}">
        <ul class="sel__sug" id="sug-${clave}" role="listbox" hidden></ul>
      </div>
      <details class="sel__todas"><summary>Ver todas (${opciones.length})</summary>
        <input type="search" class="sel__filtro" placeholder="Filtrar la lista" aria-label="Filtrar ${esc(titulo.toLowerCase())}">
        <div class="sel__lista">${opciones.map((o) => `<label class="sel__op"><input type="checkbox" value="${esc(o)}"> ${esc(o)}</label>`).join("")}</div>
      </details>
      ${otroCampo ? `<label class="prop-etq prop-etq--sub" for="otro-${clave}">${esc(otroCampo)}</label>
        <input id="otro-${clave}" class="prop-campo" type="text" placeholder="Separadas por comas" maxlength="300">` : ""}
    </section>`;
  }
  function pintarElegidas(clave) {
    const caja = $(`[data-sel="${clave}"] .sel__elegidas`);
    caja.innerHTML = [...elegidas[clave]].map((v) => `<span class="sel__chip">${esc(v)}<button type="button" data-quitar="${esc(v)}" aria-label="Quitar ${esc(v)}">✕</button></span>`).join("");
    $$(`[data-sel="${clave}"] .sel__lista input`).forEach((c) => { c.checked = elegidas[clave].has(c.value); });
  }
  function activarSelector(clave, opciones) {
    const raiz = $(`[data-sel="${clave}"]`), campo = $("input[role=combobox]", raiz), sug = $(".sel__sug", raiz);
    let marcada = 0, lista = [];
    const cerrar = () => { sug.hidden = true; campo.setAttribute("aria-expanded", "false"); };
    const elegir = (v) => { elegidas[clave].add(v); pintarElegidas(clave); campo.value = ""; cerrar(); campo.focus(); };
    const mostrar = () => {
      const q = norm(campo.value);
      if (!q) return cerrar();
      lista = opciones.filter((o) => !elegidas[clave].has(o) && norm(o).includes(q))
        .sort((a, b) => (norm(b).startsWith(q) - norm(a).startsWith(q)) || a.localeCompare(b, "es")).slice(0, 8);
      marcada = 0;
      sug.innerHTML = lista.length ? lista.map((o, i) => `<li role="option" data-v="${esc(o)}" aria-selected="${i === 0}">${esc(o)}</li>`).join("")
        : `<li class="sel__nada">Nada con «${esc(campo.value)}». Mira «Ver todas» o escríbela en «otras».</li>`;
      sug.hidden = false; campo.setAttribute("aria-expanded", "true");
    };
    campo.addEventListener("input", mostrar);
    campo.addEventListener("keydown", (e) => {
      if (sug.hidden || !lista.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); marcada = (marcada + (e.key === "ArrowDown" ? 1 : lista.length - 1)) % lista.length;
        $$("li", sug).forEach((li, i) => li.setAttribute("aria-selected", i === marcada));
      } else if (e.key === "Enter") { e.preventDefault(); elegir(lista[marcada]); }
      else if (e.key === "Escape") cerrar();
    });
    sug.addEventListener("mousedown", (e) => { const li = e.target.closest("li[data-v]"); if (li) { e.preventDefault(); elegir(li.dataset.v); } });
    campo.addEventListener("blur", () => setTimeout(cerrar, 150));
    raiz.addEventListener("click", (e) => { const b = e.target.closest("[data-quitar]"); if (b) { elegidas[clave].delete(b.dataset.quitar); pintarElegidas(clave); } });
    raiz.addEventListener("change", (e) => {
      if (!e.target.matches(".sel__lista input")) return;
      e.target.checked ? elegidas[clave].add(e.target.value) : elegidas[clave].delete(e.target.value); pintarElegidas(clave);
    });
    $(".sel__filtro", raiz).addEventListener("input", (e) => {
      const q = norm(e.target.value); $$(".sel__op", raiz).forEach((l) => { l.hidden = q && !norm(l.textContent).includes(q); });
    });
  }

  // ---------- pantalla ----------
  function html() {
    const rel = LISTAS.relevancia || {};
    const listo = servicio() && clientId();
    return `<h1 class="solo-lectores">Proponer una obra</h1>
    <form id="proponer" class="prop" novalidate>
      ${listo ? "" : `<p class="nota prop-aviso">Esta pantalla está en pruebas: falta conectar el buscador y la entrada con Google, así que todavía no se puede enviar.</p>`}
      <section class="prop-grupo">
        <h2 class="prop-h">1 · Entra con tu cuenta de Google</h2>
        <p class="prop-ayuda">Solo para evitar el spam. Tu correo no se publica.</p>
        <div id="g-boton"></div><p id="g-estado" class="prop-ayuda"></p>
      </section>
      <section class="prop-grupo">
        <h2 class="prop-h">2 · Busca la serie o película</h2>
        <p class="prop-ayuda">Pega un enlace de IMDb o de TMDB, o escribe el título. Rellenaremos lo que podamos; lo demás, a mano.</p>
        <div class="prop-fila"><input id="buscar-obra" class="prop-campo" type="text" placeholder="Enlace o título" autocomplete="off">
          <button class="boton" type="button" id="btn-buscar" ${servicio() ? "" : "disabled"}>Buscar</button></div>
        <div id="resultados" aria-live="polite"></div>
      </section>
      <section class="prop-grupo">
        <h2 class="prop-h">3 · Revisa los datos</h2>
        <div id="ya-esta" aria-live="polite"></div>
        <fieldset class="prop-radio"><legend class="prop-etq">Tipo *</legend>
          <label><input type="radio" name="Tipo" value="Serie"> Serie</label><label><input type="radio" name="Tipo" value="Película"> Película</label></fieldset>
        ${campo("Título original", "Título original *", { req: true })}
        ${campo("Título en España")}${campo("Título en Latinoamérica")}
        <div class="prop-dos">${campo("País")}${campo("Año", "Año de estreno", { tipo: "number" })}</div>
        <div class="prop-dos solo-serie">${campo("Año fin", "Año en que terminó", { tipo: "number" })}${campo("Temporada de aparición", "Temporadas con la historia")}</div>
        <label class="prop-etq" for="f-sinopsis">Sinopsis</label>
        <textarea id="f-sinopsis" name="Sinopsis" class="prop-campo" rows="5" maxlength="3000"></textarea>
        ${campo("Directore", "Dirección")}${campo("Actrices (separadas por comas)", "Actrices (separadas por comas)")}
        <img id="poster-prev" class="prop-poster" alt="" hidden>
        ${campo("Póster (enlace de la imagen)", "Póster (enlace de la imagen)", { tipo: "url" })}
        ${campo("Dónde verla (enlace)", "Dónde verla (enlace)", { tipo: "url" })}<p id="plataformas" class="prop-ayuda"></p>
        ${campo("Enlace informativo", "Enlace informativo (IMDb, Wikipedia…)", { tipo: "url" })}
        ${campo("Letterboxd (enlace)", "Letterboxd (enlace)", { tipo: "url" })}
      </section>
      <section class="prop-grupo">
        <h2 class="prop-h">4 · Lo que más nos ayuda</h2>
        ${selector("generos", "Género", LISTAS.generos)}
        ${selector("tematicas", "Temáticas", LISTAS.tematicas, "Escribe y elige de la lista. Si no sabes qué poner, abre «Ver todas».", "Otras temáticas que no estén en la lista")}
        ${selector("avisos", "Avisos de contenido", LISTAS.avisos, "Lo que alguien podría querer saber antes de verla.", "Otros avisos que no estén en la lista")}
        <fieldset class="prop-radio prop-radio--col"><legend class="prop-etq">Nivel de relevancia</legend>
          ${["A", "B", "C"].map((k) => `<label><input type="radio" name="Nivel de relevancia" value="${k}"> <b>${k}</b> · ${esc(rel[k] || "")}</label>`).join("")}</fieldset>
        <div class="prop-dos">
          <label class="prop-etq">Edad recomendada<select name="Edad recomendada" class="prop-campo"><option value="">—</option>${LISTAS.edades.map((e) => `<option>${e === "TP" ? "Todos los públicos" : e}</option>`).join("")}</select></label>
          <label class="prop-etq">¿Final feliz?<select name="Final feliz" class="prop-campo"><option value="">No lo sé</option><option>Sí</option><option>No</option></select></label>
        </div>
        <label class="prop-etq">¿Se puede ver en España?<select name="Disponible en España" class="prop-campo"><option value="">No lo sé</option><option>Sí</option><option>No</option></select></label>
      </section>
      <div class="prop-trampa" aria-hidden="true"><label>Web <input name="web" tabindex="-1" autocomplete="off"></label></div>
      <p id="prop-error" class="prop-error" role="alert"></p>
      <button class="boton prop-enviar" type="submit" ${listo ? "" : "disabled"}>Enviar propuesta</button>
      <p class="prop-ayuda">Los datos de las obras vienen de <a class="enlace-suave" href="https://www.themoviedb.org/" target="_blank" rel="noopener">TMDB</a>. Revisamos cada propuesta antes de publicarla.</p>
    </form>`;
  }
  function campo(nombre, etiqueta = nombre, { tipo = "text", req = false } = {}) {
    const id = "f-" + norm(nombre).replace(/[^a-z0-9]+/g, "-");
    return `<label class="prop-etq" for="${id}">${esc(etiqueta)}</label><input id="${id}" name="${esc(nombre)}" class="prop-campo" type="${tipo}" ${req ? "required" : ""} ${tipo === "number" ? 'min="1890" max="2100"' : 'maxlength="500"'}>`;
  }
  const poner = (nombre, v) => { const el = $(`[name="${CSS.escape(nombre)}"]`); if (el && v != null && v !== "") el.value = v; };

  // ---------- relleno desde TMDB ----------
  const paisES = (c) => { if (c === "US") return "EE.UU."; try { return new Intl.DisplayNames(["es"], { type: "region" }).of(c); } catch { return c; } };
  function rellenar(d) {
    tmdbId = (d.tipo === "serie" ? "tv/" : "movie/") + d.tmdb;
    $$(`[name="Tipo"]`).forEach((r) => { r.checked = r.value === (d.tipo === "serie" ? "Serie" : "Película"); });
    ["Título original", "Título en España", "País", "Año", "Año fin", "Temporada de aparición", "Sinopsis", "Directore", "Actrices (separadas por comas)", "Póster (enlace de la imagen)", "Enlace informativo", "Letterboxd (enlace)"]
      .forEach((n) => { const el = $(`[name="${CSS.escape(n)}"]`); if (el) el.value = ""; });
    poner("Título original", d.original); poner("Título en España", d.titulo !== d.original ? d.titulo : "");
    poner("País", d.paises.map(paisES).join(", ")); poner("Año", d.anio); poner("Año fin", d.anio_fin);
    if (d.temporadas) poner("Temporada de aparición", d.temporadas > 1 ? `1-${d.temporadas}` : "1");
    poner("Sinopsis", d.sinopsis); poner("Directore", d.direccion.join(", ")); poner("Actrices (separadas por comas)", d.actrices.join(", "));
    poner("Póster (enlace de la imagen)", d.poster); poner("Enlace informativo", d.info); poner("Letterboxd (enlace)", d.letterboxd);
    const g = new Map(LISTAS.generos.map((x) => [norm(x), x]));
    d.generos.forEach((x) => { const m = g.get(norm(x)); if (m) elegidas.generos.add(m); }); pintarElegidas("generos");
    $("#plataformas").textContent = d.plataformas_es.length ? "En España se puede ver en: " + d.plataformas_es.join(", ") + ". Pega aquí el enlace de la plataforma." : "";
    if (!d.sinopsis) $("#f-sinopsis").placeholder = "TMDB no tiene sinopsis en español: escribe una breve, por favor.";
    actualizarTipo(); prevPoster(); comprobarRepetida();
    $("#f-titulo-original").scrollIntoView({ behavior: "smooth", block: "center" });
  }
  function comprobarRepetida() {
    const t = norm($("#f-titulo-original").value), te = norm($("[name='Título en España']").value), a = parseInt($("[name='Año']").value, 10);
    const o = t && OBRAS.find((x) => (norm(x.titulo_original) === t || norm(x.titulo) === t || (te && norm(x.titulo) === te)) && (!a || !x.anio || x.anio === a));
    $("#ya-esta").innerHTML = o ? `<p class="nota">¡Ya la tenemos! <a href="#/obra/${o.id}">${esc(o.titulo)} (${o.anio || ""})</a> ya está en La Safoteca.</p>` : "";
  }
  const actualizarTipo = () => { const s = $(`[name="Tipo"]:checked`)?.value === "Serie"; $$(".solo-serie").forEach((x) => { x.hidden = !s; }); };
  function prevPoster() { const u = $("[name='Póster (enlace de la imagen)']").value, img = $("#poster-prev"); img.hidden = !/^https:\/\//.test(u); if (!img.hidden) img.src = u; }

  async function buscarObra() {
    const q = $("#buscar-obra").value.trim(), caja = $("#resultados"); if (!q) return;
    caja.innerHTML = `<p class="prop-ayuda">Buscando…</p>`;
    try {
      if (/^https?:\/\//i.test(q)) {
        const d = await pedir({ accion: "enlace", url: q }); caja.innerHTML = ""; rellenar(d);
      } else {
        const { resultados } = await pedir({ accion: "buscar", q });
        caja.innerHTML = resultados.length ? `<ul class="prop-res">${resultados.map((r) => `<li><button type="button" data-tipo="${r.tipo}" data-id="${r.id}">
          ${r.poster ? `<img src="${esc(r.poster)}" alt="" loading="lazy">` : `<span class="prop-res__sin"></span>`}
          <span><b>${esc(r.titulo)}</b>${r.original && r.original !== r.titulo ? `<br><small>${esc(r.original)}</small>` : ""}<br><small>${r.tipo === "serie" ? "Serie" : "Película"}${r.anio ? " · " + r.anio : ""}</small></span></button></li>`).join("")}</ul>`
          : `<p class="prop-ayuda">No encontramos nada con «${esc(q)}». Puedes rellenar los datos a mano.</p>`;
      }
    } catch (e) {
      caja.innerHTML = `<p class="prop-ayuda">${e.message === "letterboxd" ? "Letterboxd no deja leer sus fichas: escribe el título y elige la obra de la lista." : esc(e.message)}</p>`;
    }
  }

  // ---------- Google ----------
  function iniciarGoogle() {
    if (!clientId()) { $("#g-estado").textContent = "La entrada con Google aún no está configurada."; return; }
    const arrancar = () => {
      google.accounts.id.initialize({ client_id: clientId(), callback: (r) => {
        credencial = r.credential;
        try { ctxCuenta = JSON.parse(atob(r.credential.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).email || ""; } catch { ctxCuenta = ""; }
        $("#g-estado").textContent = ctxCuenta ? `Has entrado como ${ctxCuenta}.` : "Has entrado con Google.";
      }, auto_select: false, ux_mode: "popup" });
      google.accounts.id.renderButton($("#g-boton"), { theme: "outline", size: "large", text: "signin_with", locale: "es" });
    };
    if (window.google?.accounts?.id) return arrancar();
    const s = document.createElement("script"); s.src = "https://accounts.google.com/gsi/client"; s.async = true; s.onload = arrancar;
    s.onerror = () => { $("#g-estado").textContent = "No se ha podido cargar la entrada con Google. Comprueba tu conexión."; };
    document.head.appendChild(s);
  }

  // ---------- enviar ----------
  async function enviar(e) {
    e.preventDefault();
    const err = $("#prop-error"); err.textContent = "";
    const f = new FormData($("#proponer"));
    if (!f.get("Tipo") || !String(f.get("Título original") || "").trim()) { err.textContent = "Indica si es serie o película y su título original."; return; }
    if (!credencial) { err.textContent = "Entra con tu cuenta de Google (paso 1) para poder enviar."; return; }
    const datos = {};
    for (const [k, v] of f.entries()) if (k !== "web" && String(v).trim()) datos[k] = String(v).trim();
    if (datos["Edad recomendada"] === "Todos los públicos") datos["Edad recomendada"] = "TP";
    datos["Temática"] = [...elegidas.tematicas].join(", "); datos["Aviso"] = [...elegidas.avisos].join(", "); datos["Género"] = [...elegidas.generos].join(", ");
    datos["Otras temáticas (separadas por comas)"] = $("#otro-tematicas").value.trim(); datos["Otros avisos (separados por comas)"] = $("#otro-avisos").value.trim();
    const b = $(".prop-enviar"); b.disabled = true; b.textContent = "Enviando…";
    try {
      const r = await fetch(servicio(), { method: "POST", headers: { "Content-Type": "text/plain;charset=utf-8" }, redirect: "follow",
        body: JSON.stringify({ credencial, datos, tmdb: tmdbId, web: f.get("web") || "" }) });
      const d = await r.json(); if (d.error) throw new Error(d.error);
      $("#proponer").innerHTML = `<div class="nota prop-gracias"><p><strong>¡Gracias!</strong> Hemos recibido «${esc(datos["Título original"])}». La revisaremos antes de publicarla.</p>
        <p><a class="boton" href="#/proponer" id="otra">Proponer otra</a> <a class="boton boton--claro" href="#/">Volver al inicio</a></p></div>`;
      $("#otra").addEventListener("click", (ev) => { ev.preventDefault(); window.SafotecaProponer.pintar($("#vista"), { CFG, OBRAS }); });
      scrollTo(0, 0);
    } catch (x) { err.textContent = x.message || "No se ha podido enviar. Inténtalo de nuevo."; b.disabled = false; b.textContent = "Enviar propuesta"; }
  }

  window.SafotecaProponer = {
    async pintar(vista, ctx) {
      CFG = ctx.CFG || {}; OBRAS = ctx.OBRAS || []; tmdbId = "";
      Object.values(elegidas).forEach((s) => s.clear());
      try { if (!LISTAS) LISTAS = await (await fetch("data/formulario.json")).json(); }
      catch { vista.innerHTML = `<div class="vacio"><p>No hemos podido cargar el formulario. Comprueba tu conexión.</p></div>`; return; }
      vista.innerHTML = html();
      activarSelector("generos", LISTAS.generos); activarSelector("tematicas", LISTAS.tematicas); activarSelector("avisos", LISTAS.avisos);
      $("#btn-buscar").addEventListener("click", buscarObra);
      $("#buscar-obra").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); buscarObra(); } });
      $("#resultados").addEventListener("click", async (e) => {
        const b = e.target.closest("button[data-id]"); if (!b) return;
        $("#resultados").innerHTML = `<p class="prop-ayuda">Cargando datos…</p>`;
        try { rellenar(await pedir({ accion: "detalle", tipo: b.dataset.tipo, id: b.dataset.id })); $("#resultados").innerHTML = ""; }
        catch (x) { $("#resultados").innerHTML = `<p class="prop-ayuda">${esc(x.message)}</p>`; }
      });
      $$(`[name="Tipo"]`).forEach((r) => r.addEventListener("change", actualizarTipo)); actualizarTipo();
      ["#f-titulo-original", "[name='Título en España']", "[name='Año']"].forEach((s) => $(s).addEventListener("change", comprobarRepetida));
      $("[name='Póster (enlace de la imagen)']").addEventListener("change", prevPoster);
      $("#proponer").addEventListener("submit", enviar);
      iniciarGoogle();
    },
  };
})();
