/* La Safoteca · temas de temporada (p. ej. Halloween).
   Se carga en <head> para que no haya parpadeo. Decide el tema así:
   1) Enlaces cortos: #temanormal (aspecto normal, p. ej. para capturas promocionales) y #temahalloween.
      También vale #/?tema=halloween o #/?tema=normal. Dura mientras la pestaña esté abierta.
   2) Si no, el tema cuyas fechas incluyan el día de hoy (config.js -> temas). Fuera de fechas, aspecto normal. */
(function () {
  var cfg = (window.SAFOTECA_CONFIG || {}).temas || [];
  var COLORES = { halloween: ["#fff6ec", "#130b17"] };   // color de la barra del navegador (claro, oscuro)

  function guardar(v) { try { if (v) sessionStorage.setItem("safoteca.tema", v); else sessionStorage.removeItem("safoteca.tema"); } catch (e) { /* sin almacenamiento */ } }
  function leer() { try { return sessionStorage.getItem("safoteca.tema"); } catch (e) { return null; } }

  function porFecha() {
    var d = new Date(), hoy = ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
    for (var i = 0; i < cfg.length; i++) {
      var t = cfg[i];
      var dentro = t.desde <= t.hasta ? (hoy >= t.desde && hoy <= t.hasta)       // p. ej. 10-15 a 11-02
                                      : (hoy >= t.desde || hoy <= t.hasta);      // cruza fin de año: 12-15 a 01-06
      if (dentro) return t.id;
    }
    return null;
  }

  function aplicar() {
    var corto = /^#tema([\w-]+)$/.exec(location.hash);
    if (corto) {
      guardar(corto[1]);
      try { history.replaceState(null, "", location.pathname + location.search + "#/"); } catch (e) { /* sin historial */ }
    }
    var m = /[?&]tema=([\w-]+)/.exec(location.hash);
    if (m) guardar(m[1] === "normal" ? "normal" : m[1]);
    var previo = leer();
    var tema = previo ? (previo === "normal" ? null : previo) : porFecha();
    var raiz = document.documentElement;
    if (tema) raiz.setAttribute("data-tema", tema); else raiz.removeAttribute("data-tema");
    var c = COLORES[tema];
    if (c) {
      var metas = document.querySelectorAll('meta[name="theme-color"]');
      for (var i = 0; i < metas.length; i++) metas[i].setAttribute("content", /dark/.test(metas[i].media) ? c[1] : c[0]);
    }
  }
  aplicar();
  window.addEventListener("hashchange", aplicar);
})();
