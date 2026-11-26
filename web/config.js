// Textos que puede cambiar el equipo sin tocar el resto del código.
window.SAFOTECA_CONFIG = {
  nombre: "La Safoteca",
  lema: "Series y películas con representación lésbica y bisexual, con avisos de contenido para que decidas qué quieres ver.",
  // Nivel de relevancia: importancia y explicitud del lesbianismo dentro de la obra.
  // Si una letra se deja vacía, no se muestra su explicación.
  textoRelevancia: {
    A: "Protagonista sáfica y sexualidad relevante para la historia.",
    B: "Personaje principal sáfico pero sexualidad no relevante para la historia, o personaje secundario con cierta relevancia para la historia.",
    C: "Subtexto, o no tiene gran importancia, o ningún romance."
  },
  // Portada: grupos en el orden en que se muestran. "ids" son los números de las obras (columna Id de la plantilla).
  // Las obras que todavía no están publicadas se omiten solas y aparecen cuando se publiquen.
  // { tipo: "novedades" } muestra las 10 obras con el año de estreno más reciente (se calcula sola, no se elige a mano).
  portada: [
    { tipo: "novedades" },
    // «mas»: tarjeta «+» al final del carrusel que lleva al catálogo con ese filtro (aquí: Navidad y niveles A o B)
    { titulo: "Brasero, polvorón y bollo 🎄 🎁", ids: [92, 496, 506, 229, 497, 481], mas: "#/catalogo?tem=Navidad&rel=A%7CB" },   // Carol + las 5 recomendadas de la colección de Navidad
    { titulo: "Las cuatro de Letterboxd", ids: [93, 42, 221, 154] },   // las 4 películas mejor puntuadas en Letterboxd (oct. 2026): Retrato de una mujer en llamas 4,43 · The Handmaiden 4,39 · Mulholland Drive 4,26 · Thelma y Louise 4,23
    { titulo: "No te romperán el corazón 💖 🛡️", ids: [110, 150, 238, 237, 109, 115] },       // Imagine Me & You, La llamada, Nina's Heavenly Delights, Fried Green Tomatoes, D.E.B.S., But I'm a Cheerleader
    { titulo: "Series a las que dar una oportunidad", ids: [236, 152, 47, 53, 77] }        // South of Nowhere, Dickinson, She-Ra, Harley Quinn, Gentleman Jack
  ],
  // Temas de temporada: se activan solos entre estas fechas ("MM-DD") y vuelven al aspecto normal al terminar.
  // Vista previa en cualquier momento: #/?tema=halloween o #/?tema=navidad  (y #/?tema=normal para quitarla).
  temas: [
    { id: "halloween", desde: "10-15", hasta: "11-02" },
    { id: "navidad", desde: "11-26", hasta: "01-10" }
  ],
  // Formulario público para proponer series y películas. Se usa en la campaña, en Ajustes y cuando una búsqueda no da resultados.
  formularioAltas: "https://docs.google.com/forms/d/e/1FAIpQLSf9DUnpzeGC9c0ZuPT3o3caL02JeW5-MH8tvIEFk6g5xrjxcg/viewform",
  // Pantalla propia «Proponer una obra» (#/proponer). Si existe, sustituye al Google Form en todos los botones.
  // servicio: URL de la aplicación web de Apps Script (tools/formulario/proponer_obra.gs).
  // clientId: ID de cliente OAuth de Google Cloud para «Entrar con Google». Vacíos = pantalla en pruebas.
  proponer: { servicio: "https://script.google.com/macros/s/AKfycbzcICGH8caFcHjPpJs83w8u7uUKCX-BA0ok0MFD4VkokYP9UNwPK6COjjT0xWrilfB_/exec", clientId: "963227097109-tgn6p1hm3l6u197pvvd1et2kik41pmna.apps.googleusercontent.com" },
  // Cuentas (opcional): guardar favoritos y listas con Google (Firebase, plan gratuito). null = sin cuentas.
  // firebase: el bloque «firebaseConfig» de la consola de Firebase (no son claves secretas: lo protegen las reglas).
  // recaptcha: clave de SITIO de reCAPTCHA v3 para App Check (la clave secreta se queda en Firebase, nunca aquí).
  // entorno: "pre" en la rama uat y "pro" en main (los datos de pruebas no se mezclan con los reales).
  // Guía: retrospectiva técnica, W16 «Cuentas».
  cuentas: {
    firebase: {
      apiKey: "AIzaSyBog9z9ARp-TGAUo38agxyPcr6r2wMdgsY",
      authDomain: "lasafoteca-e3680.firebaseapp.com",
      projectId: "lasafoteca-e3680",
      storageBucket: "lasafoteca-e3680.firebasestorage.app",
      messagingSenderId: "963227097109",
      appId: "1:963227097109:web:cdca30d6268112143c961c",
    },
    recaptcha: "6Ld5zTMuAAAAADey_LNn-F3B8ciODKVBoIxXsqcX",   // clave de SITIO de reCAPTCHA v3 (pública); la secreta está en Firebase
    entorno: "pro",
  },
  // Campaña con barra de progreso en el Inicio. Se muestra solo entre "desde" y "hasta" (AAAA-MM-DD).
  // La barra cuenta las obras publicadas desde la fecha "desde" (se calcula sola, no se edita a mano).
  // Para una campaña nueva, cambia "id" (así vuelve a salir a quien cerró la anterior), las fechas y el objetivo.
  campana: { id: "oct2026", desde: "2026-10-13", hasta: "2026-11-20", objetivo: 25 },
  // Botón «avisar de un enlace roto» en las fichas. Se rellena con el bloque que escribe el script
  // tools/formulario/reportar_enlaces.gs al ejecutarlo; mientras sea null el botón no aparece.
  reporteEnlaces: { url: "https://docs.google.com/forms/d/e/1FAIpQLSd21ZYeq0VawPGXW_RAt1R-Pgg6dCYQZMHxrPwxp0c4lwjfJg/viewform", campos: { id: "entry.1329433313", obra: "entry.1547440425", plataforma: "entry.110345365", enlace: "entry.682423969" }},
  // Estadísticas de visitas anónimas, sin cookies (GoatCounter). Solo cuentan en la web oficial, nunca en PRE.
  // Panel: https://lasafoteca.goatcounter.com · null = sin estadísticas.
  estadisticas: "https://lasafoteca.goatcounter.com/count",
  // Opcional: enlace o correo para sugerencias (por ejemplo "mailto:..." o una URL).
  contacto: "",
  // Obras relacionadas: se calculan al exportar los datos (tools/relacionadas.py, donde están los pesos).
};
