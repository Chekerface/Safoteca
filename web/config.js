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
    { titulo: "Lesbi-halloween 🎃 🕷️", ids: [46, 114, 42, 90, 89, 51, 57, 43, 32] },       // All Cheerleaders Die, Jennifer's Body, The Handmaiden, Bly Manor, Buffy, Casa Búho, Charmed, Wynonna Earp, Motherland
    { titulo: "Las cuatro de Letterboxd", ids: [93, 42, 221, 154] },   // las 4 películas mejor puntuadas en Letterboxd (oct. 2026): Retrato de una mujer en llamas 4,43 · The Handmaiden 4,39 · Mulholland Drive 4,26 · Thelma y Louise 4,23
    { titulo: "No te romperán el corazón 💖 🛡️", ids: [110, 150, 238, 237, 109, 115] },       // Imagine Me & You, La llamada, Nina's Heavenly Delights, Fried Green Tomatoes, D.E.B.S., But I'm a Cheerleader
    { titulo: "Series a las que dar una oportunidad", ids: [236, 152, 47, 53, 77] }        // South of Nowhere, Dickinson, She-Ra, Harley Quinn, Gentleman Jack
  ],
  // Temas de temporada: se activan solos entre estas fechas ("MM-DD") y vuelven al aspecto normal al terminar.
  // Vista previa en cualquier momento: lasafoteca.com/#temahalloween  (y /#temanormal para quitarla, p. ej. para capturas).
  temas: [
    { id: "halloween", desde: "10-15", hasta: "11-02" }
  ],
  // Formulario público para proponer series y películas. Se usa en la campaña, en Ajustes y cuando una búsqueda no da resultados.
  formularioAltas: "https://docs.google.com/forms/d/e/1FAIpQLSfX88UDkjQ5l10bq8YWujj9GjdcB_9ogv6FMOpF9M0GUQlWgA/viewform",
  // Campaña con barra de progreso en el Inicio. Se muestra solo entre "desde" y "hasta" (AAAA-MM-DD).
  // La barra cuenta las obras publicadas desde la fecha "desde" (se calcula sola, no se edita a mano).
  // Para una campaña nueva, cambia "id" (así vuelve a salir a quien cerró la anterior), las fechas y el objetivo.
  campana: { id: "oct2026", desde: "2026-10-13", hasta: "2026-11-30", objetivo: 25 },
  // Botón «avisar de un enlace roto» en las fichas. Se rellena con el bloque que escribe el script
  // tools/formulario/reportar_enlaces.gs al ejecutarlo; mientras sea null el botón no aparece.
  reporteEnlaces: { url: "https://docs.google.com/forms/d/e/1FAIpQLSd21ZYeq0VawPGXW_RAt1R-Pgg6dCYQZMHxrPwxp0c4lwjfJg/viewform", campos: { id: "entry.1329433313", obra: "entry.1547440425", plataforma: "entry.110345365", enlace: "entry.682423969" }},
  // Opcional: enlace o correo para sugerencias (por ejemplo "mailto:..." o una URL).
  contacto: ""
};
