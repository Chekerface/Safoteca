/**
 * La Safoteca · formulario para añadir obras (generado por tools/generar_formulario.py).
 *
 * Cómo usarlo (una sola vez):
 *  1. Entra en https://script.google.com con la cuenta de Google del proyecto y pulsa «Nuevo proyecto».
 *  2. Borra el código que aparece y pega TODO este archivo. Guarda (icono del disquete).
 *  3. Arriba, en el desplegable de funciones, elige `crearFormulario` y pulsa «Ejecutar».
 *     La primera vez Google pide permisos (Formularios, Hojas de cálculo y Drive): acéptalos.
 *  4. Abajo, en el «Registro de ejecución», salen los enlaces: el del formulario para compartir con el equipo
 *     y el de la hoja donde se guardan las respuestas.
 *
 * Para cargar las respuestas: en la hoja de respuestas, Archivo → Descargar → Microsoft Excel (.xlsx)
 * y ejecuta `python tools/importar_formulario.py respuestas.xlsx` (con --simular para probar).
 *
 * Si cambia el catálogo (géneros, temáticas o avisos nuevos): genera el script otra vez, pégalo y ejecuta
 * `actualizarListas`: actualiza las opciones del formulario que ya existe, sin perder respuestas.
 */

var DATOS = {
 "generos": [
  {
   "titulo": "Género",
   "rango": "",
   "opciones": [
    "Acción",
    "Animación",
    "Anime",
    "Aventura",
    "Biográfico",
    "Ciencia Ficción",
    "Comedia",
    "Comedia Dramática",
    "Comedia Negra",
    "Comedia romántica",
    "Costumbrismo",
    "De época",
    "Deportes",
    "Distopía",
    "Documental",
    "Drama",
    "Día a Día",
    "Fantasía",
    "Fantástico",
    "Ficción Sobrenatural",
    "Histórico",
    "Horror",
    "Intriga",
    "Musical",
    "Policiaca",
    "Policíaca",
    "Reality",
    "Romance",
    "Sitcom",
    "Suspense",
    "Telenovela",
    "Terror",
    "Thriller",
    "Tragedia",
    "Western"
   ]
  }
 ],
 "tematicas": [
  {
   "titulo": "Temática (parte 1 de 4)",
   "rango": "de «\"Cosas de chicas\"» a «Costumbrismo»",
   "opciones": [
    "\"Cosas de chicas\"",
    "A fuego lento",
    "Aborto",
    "Acción",
    "Aceptación de la sexualidad",
    "Acoso",
    "Acoso escolar",
    "Adolescencia",
    "Adopción",
    "Adorabilidad Absoluta",
    "Afroamericanos",
    "Ajedrez",
    "Alcoholismo",
    "Amigas de la infancia",
    "Amistad",
    "Amor",
    "Amor de juventud",
    "Anacronismos",
    "Angustia",
    "Angustia adolescente",
    "Animación",
    "Anime",
    "Anticapitalista",
    "Antiheroína",
    "Asesinato",
    "Asesinatos en Serie",
    "Asia",
    "Autismo",
    "Autodescubrimiento",
    "Autopublicación",
    "Aventura",
    "Aventuras",
    "Años 30",
    "Años 40",
    "Años 50",
    "Años 60",
    "Años 70",
    "Años 80",
    "Años 90",
    "Bajo presupuesto",
    "BD",
    "Biográfico",
    "Bisexual",
    "Bisexualidad",
    "Body Horror",
    "Bomberos",
    "Brujas",
    "Brujería",
    "Bullying",
    "Butch",
    "Búsqueda de un propósito",
    "Casanova",
    "Cazadores",
    "Celos",
    "Chantaje",
    "China",
    "Ciencia Ficción",
    "Cine independiente USA",
    "Cine negro",
    "Civilizaciones perdidas",
    "Clase alta",
    "Comedia",
    "Comedia absurda",
    "Comedia de Enredo",
    "Comedia de situación",
    "Comedia Dramática",
    "Comedia Española",
    "Comedia involuntaria",
    "Comedia juvenil",
    "Comedia Negra",
    "Comedia romántica",
    "Comedia sexual",
    "Comida",
    "Coming of age",
    "Conspiraciones",
    "Consumo de drogas",
    "Cosplay",
    "Costumbrismo"
   ]
  },
  {
   "titulo": "Temática (parte 2 de 4)",
   "rango": "de «Crimen» a «Hospital»",
   "opciones": [
    "Crimen",
    "Cutre",
    "Cómic",
    "Cómic de autor",
    "Cómic indie",
    "Cómic infantil",
    "Cómic Juvenil",
    "Cómic mainstream",
    "DC",
    "De amigas a amantes",
    "De enemigas a amantes",
    "De época",
    "Delincuencia",
    "Demisexualidad",
    "Deportes",
    "Desamor",
    "Desapariciones",
    "Diferencia de altura",
    "Diferencia de clase",
    "Diferencia de edad",
    "Diferencias de clase social",
    "Discriminación fuerte",
    "Distopía",
    "Divorcio",
    "Documental",
    "Drama",
    "Drama Adolescente",
    "Drama médico",
    "Drama psicológico",
    "Drogodependencia",
    "Día a día",
    "Día de Acción de Gracias",
    "Ecchi (picante)",
    "Educativo",
    "Efectos especiales malos",
    "Embarazo adolescente",
    "Enemies to Lovers",
    "Enfermedad",
    "Entorno familiar negativo",
    "Entrada en la madurez",
    "Episodio musical",
    "Erotismo",
    "Erótico",
    "Erótico-festivo",
    "Escocia",
    "Escuela",
    "Espacio",
    "Espectáculo",
    "Espionaje",
    "Fake dating",
    "Familia",
    "Familia encontrada",
    "Family Friendly",
    "Fanfic",
    "Fantasmas",
    "Fantasía",
    "Fantasía Oscura",
    "Fantástico",
    "Fanzine",
    "Fascismo",
    "Feminismo",
    "Ficción Sobrenatural",
    "Fluidez de género",
    "Friends to Lovers",
    "Furry",
    "Futuro postapocalíptico",
    "Gran empresa",
    "Guerra",
    "Guerra Fría",
    "Hacker",
    "Halloween",
    "Heartwarming",
    "Histórico",
    "Hombres lobo",
    "Homofobia",
    "Homosexualidad",
    "Horror",
    "Hospital"
   ]
  },
  {
   "titulo": "Temática (parte 3 de 4)",
   "rango": "de «Humor» a «Relaciones complicadas»",
   "opciones": [
    "Humor",
    "Humor negro",
    "Identidad",
    "Inclusión",
    "India",
    "Inexactitud histórica",
    "Infancia",
    "Infidelidad",
    "Instituto",
    "Intercambio de parejas",
    "Internet",
    "Intriga",
    "IRA",
    "Irlanda",
    "Irlanda del Norte",
    "Juvenil",
    "Juventud",
    "Lesbiana",
    "Lesbianismo",
    "Lesbofobia",
    "Lipstick lesbian",
    "Literatura",
    "Machismo",
    "Mafia",
    "Magia",
    "Mainstream USA",
    "Mala con ganas",
    "Manga",
    "Maternidad",
    "Matrimonio",
    "Mercenarios",
    "Miedo",
    "Militancia",
    "Militarismo",
    "Misterio",
    "Mitología",
    "Mitología retocada",
    "Mitos del Amor Romántico",
    "Moda",
    "Monstruos",
    "Movimiento por los Derechos civiles",
    "Mujeres adultas",
    "Musical",
    "Muñecos",
    "Música",
    "Navidad",
    "No binarie",
    "No heartwarming",
    "Novela Rosa",
    "NSFW",
    "Pandemia",
    "Pandilla",
    "Pareja",
    "Pareja idiota",
    "Pareja sana",
    "Pareja tóxica",
    "Piratas",
    "Poliamor",
    "Policía",
    "Policíaca",
    "Política",
    "Postapocalíptico",
    "Prisión",
    "Prom",
    "Prostitución",
    "Protagonista Idiota",
    "Protagonista lesbiana",
    "Protagonistas con pocas luces",
    "Pseudoincesto",
    "PseudoReality Show",
    "Psicológico",
    "Racismo",
    "Realeza",
    "Realismo mágico",
    "Reality",
    "Redes Sociales",
    "Relaciones",
    "Relaciones complicadas"
   ]
  },
  {
   "titulo": "Temática (parte 4 de 4)",
   "rango": "de «Relaciones interpersonales» a «Épica»",
   "opciones": [
    "Relaciones interpersonales",
    "Relación de pareja",
    "Relación interracial",
    "Religión",
    "Remake",
    "Represión",
    "Riqueza",
    "Road Movie",
    "Robots",
    "Romance",
    "Romance de instituto",
    "Romance en el trabajo",
    "Roommates",
    "Salir del armario",
    "Salud Mental",
    "Salvar al mundo",
    "Sectas",
    "Secuela",
    "Secuestros",
    "Serie de antología",
    "Series que parecen fics",
    "Sexo",
    "Sexualidad",
    "Sicaria",
    "Siglo XIX",
    "Siglo XVII",
    "Sitcom",
    "Slasher",
    "Sobrenatural",
    "Soledad",
    "Sororidad",
    "Space opera",
    "Spin-off",
    "Stand-up",
    "Subtexto",
    "Superheroinas",
    "Superhéroes",
    "Supervivencia",
    "Supporting Dad",
    "Supporting Mom",
    "Surrealismo",
    "Suspense",
    "Teatro",
    "Telenovela",
    "Terror",
    "Terrorismo",
    "Thriller",
    "Thriller psicológico",
    "TLP",
    "Tragedia",
    "Trans",
    "Transfobia",
    "Trastornos mentales",
    "Travestismo",
    "Triángulo amoroso",
    "Universidad",
    "Universos alternativos",
    "Vampiras",
    "Vecinos",
    "Vejez",
    "Venganza",
    "Viaje en carretera",
    "Viajes en el tiempo",
    "Vida",
    "Vida adulta",
    "Vida nocturna",
    "Vida Rural",
    "Vida Sexual",
    "Vikingas lesbianas",
    "Violencia",
    "Webserie",
    "Western",
    "WTF?!",
    "Young Adult",
    "Yuri",
    "Zombies",
    "Épica"
   ]
  }
 ],
 "avisos": [
  {
   "titulo": "Aviso",
   "rango": "",
   "opciones": [
    "Abuso",
    "Abuso sexual",
    "Abuso sexual implícito",
    "Accidente de tráfico",
    "Acoso",
    "Acoso escolar",
    "Acoso sexual",
    "Adorabilidad absoluta",
    "Alcoholismo",
    "Angustia",
    "Angustia existencial",
    "Ansiedad",
    "Apropiación cultural",
    "Asesinato",
    "Autolesión",
    "BDSM",
    "Bifobia",
    "Body Horror",
    "Brutalidad policial",
    "Cancelada",
    "Capacitismo",
    "Chantaje",
    "Chantaje emocional",
    "Chistes hirientes",
    "Consentimiento dudoso",
    "Consumo de alcohol",
    "Consumo de drogas",
    "Contenido Cuestionable",
    "Cruda",
    "Crímenes de guerra",
    "Cáncer",
    "Delincuencia",
    "Depresión",
    "Desamor",
    "Desnudos",
    "Diferencia de edad",
    "Discriminación",
    "Discriminación fuerte",
    "Discriminación leve",
    "Drogodependencia",
    "Duelo",
    "Echar de casa",
    "Enfermedad Mental",
    "Engaños y Mentiras",
    "Erotismo",
    "Exotismo",
    "Genocidio",
    "Gordofobia",
    "Gore",
    "Hate sex",
    "Homofobia",
    "Homofobia leve",
    "Ideas suicidas",
    "Incesto",
    "Incesto en segundo grado",
    "Infidelidad",
    "Intento de abuso sexual",
    "Lesbofobia",
    "Madre lgbtfóbica",
    "Maltrato",
    "Maltrato animal",
    "Manipulación",
    "Mentiras y Engaño",
    "Muerte",
    "Muerte de personaje importante",
    "Muerte y Destrucción",
    "Obsesión",
    "Padre lgbtfobo",
    "Padre lgtbfobo",
    "Pareja tóxica",
    "Pederastia",
    "Plumofobia",
    "Prostitución",
    "Pseudoincesto",
    "Psicópata",
    "Racismo",
    "Religión",
    "Ritos extraños",
    "Sangre",
    "Sangre/Gore",
    "Secuestro",
    "Sexo Explícito",
    "Sexo Implícito",
    "Sexualización",
    "Sida",
    "Sin hogar",
    "Suicidio",
    "Síndrome de la lesbiana muerta",
    "TCA",
    "Tiroteo",
    "Tiroteo escolar",
    "Tortura",
    "Transfobia",
    "Violación",
    "Violencia",
    "Violencia de género",
    "Violencia explícita",
    "Violencia leve",
    "Vómitos"
   ]
  }
 ],
 "relevancia": {
  "A": "Protagonista sáfica y sexualidad relevante para la historia.",
  "B": "Personaje principal sáfico pero sexualidad no relevante para la historia, o personaje secundario con cierta relevancia para la historia.",
  "C": "Subtexto, o no tiene gran importancia, o ningún romance."
 }
};

var TITULO_FORMULARIO = "La Safoteca · Añadir una serie o película";
var CLAVE_ID = "ID_FORMULARIO";

function crearFormulario() {
  var f = FormApp.create(TITULO_FORMULARIO);
  f.setDescription(
    "Rellena una ficha por cada obra. Solo son obligatorios el tipo, el título original, la sinopsis y el nivel de relevancia. " +
    "Si no sabes algo, déjalo en blanco. Para añadir varias obras, envía el formulario varias veces.");
  f.setCollectEmail(true);          // el correo queda como «revisore»
  f.setAllowResponseEdits(false);
  f.setProgressBar(true);
  f.setConfirmationMessage("¡Gracias! La obra se revisará antes de publicarse.");

  f.addMultipleChoiceItem().setTitle("Tipo").setChoiceValues(["Película", "Serie", "Libro", "Cómic"]).setRequired(true);
  f.addTextItem().setTitle("Título original").setRequired(true)
    .setHelpText("Tal y como se llama en su idioma original.");
  f.addTextItem().setTitle("Título en España");
  f.addTextItem().setTitle("Título en Latinoamérica");
  f.addTextItem().setTitle("País").setHelpText("Por ejemplo: EE.UU., España, Reino Unido, Corea del Sur…");
  f.addTextItem().setTitle("Año")
    .setHelpText("Año de estreno (en series, el de la primera temporada). Vale «2019» o un rango «2013-2019».")
    .setValidation(FormApp.createTextValidation().setHelpText("Escribe un año de 4 cifras, por ejemplo 2019 o 2013-2019")
      .requireTextMatchesPattern("^\\s*\\d{4}\\s*([-–]\\s*(\\d{4})?)?\\s*$").build());
  f.addTextItem().setTitle("Año fin").setHelpText("Solo series que ya han terminado.");
  f.addParagraphTextItem().setTitle("Sinopsis").setRequired(true);
  f.addTextItem().setTitle("Temporada de aparición").setHelpText("Solo series: en qué temporadas hay representación. Ej.: «1 y 2».");

  var rel = DATOS.relevancia;
  f.addMultipleChoiceItem().setTitle("Nivel de relevancia").setRequired(true)
    .setChoiceValues(["A", "B", "C"])
    .setHelpText("A: " + rel.A + "\nB: " + rel.B + "\nC: " + rel.C);
  f.addListItem().setTitle("Edad recomendada")
    .setChoiceValues(["TP","0","3","6","7","9","11","12","13","14","15","16","17","18"]);

  DATOS.generos.forEach(function (g) {
    f.addCheckboxItem().setTitle(g.titulo).setChoiceValues(g.opciones).setHelpText("Marca todos los que apliquen.");
  });
  f.addTextItem().setTitle("Directore").setHelpText("Si son varies, sepáralos con comas.");
  f.addParagraphTextItem().setTitle("Actrices (separadas por comas)");

  DATOS.tematicas.forEach(function (g, i) {
    var it = f.addCheckboxItem().setTitle(g.titulo).setChoiceValues(g.opciones)
      .setHelpText("Marca todas las que apliquen. Esta parte va " + g.rango + " (orden alfabético).");
    if (i === DATOS.tematicas.length - 1) it.showOtherOption(true);   // «Otro»: temática nueva, queda pendiente de revisión
  });
  DATOS.avisos.forEach(function (g, i) {
    var it = f.addCheckboxItem().setTitle(g.titulo).setChoiceValues(g.opciones)
      .setHelpText("Avisos de contenido (TW). Marca todos los que apliquen." + (g.rango ? " Esta parte va " + g.rango + "." : ""));
    if (i === DATOS.avisos.length - 1) it.showOtherOption(true);
  });

  f.addMultipleChoiceItem().setTitle("Disponible en España").setChoiceValues(["Sí", "No"]);
  f.addMultipleChoiceItem().setTitle("Final feliz").setChoiceValues(["Sí", "No"]);
  f.addParagraphTextItem().setTitle("Dónde verla (enlace)")
    .setHelpText("Enlace a la ficha en la plataforma (Netflix, Prime, Filmin…). Puedes poner varios, uno por línea. No enlaces webs piratas.");
  f.addTextItem().setTitle("Enlace informativo").setHelpText("FilmAffinity, IMDb o Wikipedia.");
  f.addTextItem().setTitle("Póster (enlace de la imagen)").setHelpText("Dirección de una imagen (termina en .jpg, .png o .webp).");
  f.addTextItem().setTitle("Letterboxd (enlace)").setHelpText("Solo películas.");

  // Hoja de respuestas enlazada
  var hoja = SpreadsheetApp.create("La Safoteca · Respuestas del formulario");
  f.setDestination(FormApp.DestinationType.SPREADSHEET, hoja.getId());

  PropertiesService.getScriptProperties().setProperty(CLAVE_ID, f.getId());
  Logger.log("Formulario (para editar): " + f.getEditUrl());
  Logger.log("Formulario (para compartir con el equipo): " + f.getPublishedUrl());
  Logger.log("Hoja de respuestas: " + hoja.getUrl());
}

/** Actualiza las opciones de géneros, temáticas y avisos del formulario ya creado. */
function actualizarListas() {
  var id = PropertiesService.getScriptProperties().getProperty(CLAVE_ID);
  if (!id) throw new Error("No hay formulario guardado: ejecuta primero crearFormulario.");
  var f = FormApp.openById(id);
  var grupos = DATOS.generos.concat(DATOS.tematicas, DATOS.avisos);
  var cambiados = 0;
  f.getItems(FormApp.ItemType.CHECKBOX).forEach(function (item) {
    grupos.forEach(function (g) {
      if (item.getTitle() === g.titulo) { item.asCheckboxItem().setChoiceValues(g.opciones); cambiados++; }
    });
  });
  Logger.log("Listas actualizadas: " + cambiados + " preguntas.");
  if (cambiados < grupos.length) Logger.log("Aviso: han cambiado los tramos (títulos) de alguna lista; crea un formulario nuevo con crearFormulario.");
}
