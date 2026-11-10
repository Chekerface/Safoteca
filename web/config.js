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
  // Campaña con barra de progreso en el Inicio. Se muestra solo entre "desde" y "hasta" (AAAA-MM-DD).
  // La barra cuenta las obras publicadas desde la fecha "desde" (se calcula sola, no se edita a mano).
  // Para una campaña nueva, cambia "id" (así vuelve a salir a quien cerró la anterior), las fechas y el objetivo.
  campana: { id: "oct2026", desde: "2026-10-13", hasta: "2026-11-30", objetivo: 25 },
  // Botón «avisar de un enlace roto» en las fichas. Se rellena con el bloque que escribe el script
  // tools/formulario/reportar_enlaces.gs al ejecutarlo; mientras sea null el botón no aparece.
  reporteEnlaces: { url: "https://docs.google.com/forms/d/e/1FAIpQLSd21ZYeq0VawPGXW_RAt1R-Pgg6dCYQZMHxrPwxp0c4lwjfJg/viewform", campos: { id: "entry.1329433313", obra: "entry.1547440425", plataforma: "entry.110345365", enlace: "entry.682423969" }},
  // Opcional: enlace o correo para sugerencias (por ejemplo "mailto:..." o una URL).
  contacto: "",
  // Obras relacionadas (carrusel al final de la ficha). Todo se ajusta aquí.
  relacionadas: {
    max: 10,              // tarjetas que se muestran
    minimo: 3,            // puntos mínimos para considerarse relacionada
    topeTematicas: 6,     // tope de puntos que aportan las temáticas
    pesos: { tematica: 1, genero: 2, director: 5, actriz: 2 },
    exigirFinalFeliz: true, // si la ficha tiene final feliz, solo se recomiendan obras con final feliz
    mismoTipo: false      // true = solo obras del mismo tipo (serie/película)
  }
};
