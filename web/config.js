// Textos que puede cambiar el equipo sin tocar el resto del código.
window.SAFOTECA_CONFIG = {
  nombre: "La Safoteca",
  lema: "Series y películas con representación lésbica y bisexual, con avisos de contenido para que decidas qué quieres ver.",
  // Nivel de relevancia: importancia y explicitud del lesbianismo dentro de la obra.
  // Si una letra se deja vacía, no se muestra su explicación.
  textoRelevancia: {
    A: "Protagonista y relevante para la historia.",
    B: "Personaje principal pero no relevante, o personaje secundario con cierta relevancia para la historia.",
    C: "Subtexto, o no tiene gran importancia, o ningún romance."
  },
  // Portada: grupos en el orden en que se muestran. "ids" son los números de las obras (columna Id de la plantilla).
  // Las obras que todavía no están publicadas se omiten solas y aparecen cuando se publiquen.
  // { tipo: "novedades" } muestra las últimas obras añadidas.
  portada: [
    { titulo: "Lesbi-halloween 🎃 🕷️", ids: [46, 114, 42, 90, 89, 51, 57, 43, 32] },       // All Cheerleaders Die, Jennifer's Body, The Handmaiden, Bly Manor, Buffy, Casa Búho, Charmed, Wynonna Earp, Motherland
    { tipo: "novedades" },
    { titulo: "No te romperán el corazón 💖 🛡️", ids: [110, 150, 109, 115] },              // Imagine Me & You, La llamada, D.E.B.S., But I'm a Cheerleader (faltan en la base: Nina's Heavenly Delights, Fried Green Tomatoes)
    { titulo: "Series a las que darle una oportunidad", ids: [152, 47, 53, 77] }            // Dickinson, She-Ra, Harley Quinn, Gentleman Jack (falta en la base: South of Nowhere)
  ],
  // Opcional: enlace o correo para sugerencias (por ejemplo "mailto:..." o una URL).
  contacto: ""
};
