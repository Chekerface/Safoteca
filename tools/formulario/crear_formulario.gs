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
 * El formulario se pone al día SOLO: una vez, ejecuta `instalarSincronizacionDiaria`. Desde entonces, cada noche
 * `sincronizarListas` lee las listas de https://www.lasafoteca.com/data/formulario.json (las que publica la web
 * al mergear una importación) y cambia las opciones de géneros, temáticas y avisos, sin perder respuestas.
 * Si algo falla, Google te manda un correo. `actualizarListas` sigue sirviendo para ponerlo al día a mano
 * con las listas pegadas en este archivo.
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
    "Biográfico",
    "Ciencia ficción",
    "Comedia",
    "Comedia romántica",
    "Documental",
    "Drama",
    "Fantasía",
    "Histórico",
    "Intriga",
    "Musical",
    "Policíaca",
    "Reality",
    "Romance",
    "Telenovela",
    "Terror",
    "Thriller",
    "Western"
   ]
  }
 ],
 "tematicas": [
  {
   "titulo": "Temática (parte 1 de 4)",
   "rango": "de «\"Cosas de chicas\"» a «Cómic mainstream»",
   "opciones": [
    "\"Cosas de chicas\"",
    "Aborto",
    "Aceptación de la sexualidad",
    "Acoso",
    "Acoso escolar",
    "Adolescencia",
    "Adopción",
    "Afroamericanos",
    "Ajedrez",
    "Alcoholismo",
    "Amigas de la infancia",
    "Amistad",
    "Amor",
    "Amor de juventud",
    "Amor imposible",
    "Anacronismos",
    "Angustia",
    "Angustia adolescente",
    "Anticapitalista",
    "Antiheroína",
    "Asesinato",
    "Asesinatos en Serie",
    "Asia",
    "Autismo",
    "Autodescubrimiento",
    "Autopublicación",
    "Aventura",
    "Años 30",
    "Años 40",
    "Años 50",
    "Años 60",
    "Años 70",
    "Años 80",
    "Años 90",
    "Bajo presupuesto",
    "BD",
    "Bisexual",
    "Bisexualidad",
    "Body Horror",
    "Bomberos",
    "Brujas",
    "Brujería",
    "Butch",
    "Búsqueda de un propósito",
    "Casanova",
    "Cazadores",
    "Celos",
    "Chantaje",
    "China",
    "Cine independiente USA",
    "Cine negro",
    "Civilizaciones perdidas",
    "Clase alta",
    "Comedia absurda",
    "Comedia de enredo",
    "Comedia de situación",
    "Comedia dramática",
    "Comedia española",
    "Comedia involuntaria",
    "Comedia juvenil",
    "Comedia sexual",
    "Comida",
    "Coming of age",
    "Conspiraciones",
    "Corrupción policial",
    "Cosplay",
    "Costumbrismo",
    "Crimen",
    "Cutre",
    "Cómic",
    "Cómic de autor",
    "Cómic indie",
    "Cómic infantil",
    "Cómic juvenil",
    "Cómic mainstream"
   ]
  },
  {
   "titulo": "Temática (parte 2 de 4)",
   "rango": "de «DC» a «IRA»",
   "opciones": [
    "DC",
    "De amigas a amantes",
    "De época",
    "Delincuencia",
    "Demisexualidad",
    "Deportes",
    "Desamor",
    "Desapariciones",
    "Diferencia de altura",
    "Diferencia de edad",
    "Diferencias de clase social",
    "Discriminación",
    "Distopía",
    "Divorcio",
    "Drama adolescente",
    "Drama médico",
    "Drama psicológico",
    "Drogodependencia",
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
    "Erótico",
    "Erótico-festivo",
    "Escocia",
    "Escritora",
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
    "Fantasía oscura",
    "Fanzine",
    "Fascismo",
    "Feminismo",
    "Ficción sobrenatural",
    "Fiestas",
    "Fluidez de género",
    "Friends to lovers",
    "Furry",
    "Gran empresa",
    "Guardaespaldas",
    "Guerra",
    "Guerra Fría",
    "Hacker",
    "Halloween",
    "Heartwarming",
    "Heterosexual",
    "Hombres lobo",
    "Homofobia",
    "Homosexualidad",
    "Hospital",
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
    "IRA"
   ]
  },
  {
   "titulo": "Temática (parte 3 de 4)",
   "rango": "de «Irlanda» a «Romance en el trabajo»",
   "opciones": [
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
    "Madre soltera",
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
    "Muñecos",
    "Música",
    "Naturaleza",
    "Navidad",
    "No binarie",
    "No heartwarming",
    "Novela Rosa",
    "NSFW",
    "Pandemia",
    "Pandilla",
    "Pareja idiota",
    "Pareja sana",
    "Piratas",
    "Poliamor",
    "Policía",
    "Política",
    "Postapocalíptico",
    "Prisión",
    "Prom",
    "Prostitución",
    "Protagonista Idiota",
    "Protagonista lesbiana",
    "Protagonistas con pocas luces",
    "PseudoReality Show",
    "Psicológico",
    "Pueblo pequeño",
    "Pérdida de memoria",
    "Pérdida de un ser querido",
    "Racismo",
    "Realeza",
    "Realismo mágico",
    "Redes Sociales",
    "Relaciones",
    "Relaciones complicadas",
    "Relaciones interpersonales",
    "Relación de pareja",
    "Religión",
    "Remake",
    "Represión",
    "Riqueza",
    "Rivalidad familiar",
    "Road Movie",
    "Robots",
    "Romance de instituto",
    "Romance en el trabajo"
   ]
  },
  {
   "titulo": "Temática (parte 4 de 4)",
   "rango": "de «Romcom» a «Épica»",
   "opciones": [
    "Romcom",
    "Roommates",
    "Salir del armario",
    "Salud Mental",
    "Salvar al mundo",
    "San Valentín",
    "Secretos",
    "Sectas",
    "Secuela",
    "Secuestros",
    "Segundas oportunidades",
    "Serie Coral",
    "Serie de antología",
    "Series que parecen fics",
    "Sexualidad",
    "Sicaria",
    "Siglo XIX",
    "Siglo XVII",
    "Sitcom",
    "Slasher",
    "Slow burn",
    "Sobrenatural",
    "Sobriedad",
    "Soledad",
    "Soltería",
    "Sororidad",
    "Space opera",
    "Spin-off",
    "Stand-up",
    "Subtexto",
    "Sugar baby",
    "Sugar mommy",
    "Superheroinas",
    "Superhéroes",
    "Supervivencia",
    "Suplantación de identidad",
    "Supporting Dad",
    "Supporting Mom",
    "Surrealismo",
    "Suspense",
    "Teatro",
    "Tello",
    "Terrorismo",
    "Thai GL",
    "The 4 elements",
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
    "Viajes en el tiempo",
    "Vida",
    "Vida adulta",
    "Vida nocturna",
    "Vida Rural",
    "Vida Sexual",
    "Vikingas lesbianas",
    "Violencia",
    "Webserie",
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
    "Canibalismo",
    "Capacitismo",
    "Celos",
    "Chantaje",
    "Chantaje emocional",
    "Chistes hirientes",
    "Conductas perjudiciales",
    "Consentimiento dudoso",
    "Consumo de alcohol",
    "Consumo de drogas",
    "Contenido Cuestionable",
    "Crimen",
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
    "Enfermedad",
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
    "Muerte",
    "Muerte de personaje importante",
    "Muerte y Destrucción",
    "Obsesión",
    "Padre lgbtfóbico",
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
    "Secuestro",
    "Sexo",
    "Sexo explícito",
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
// Solo si actualizarListas dice que no sabe qué formulario es: pega aquí su enlace de edición (el que acaba en /edit)
var URL_EDICION = "";

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

/** Actualiza las opciones de géneros, temáticas y avisos del formulario ya creado (sin tocar nada más ni perder respuestas). */
function actualizarListas(listas) {
  if (listas && listas.generos) DATOS.generos = listas.generos, DATOS.tematicas = listas.tematicas, DATOS.avisos = listas.avisos;
  var id = PropertiesService.getScriptProperties().getProperty(CLAVE_ID);
  if (!id && URL_EDICION) id = FormApp.openByUrl(URL_EDICION).getId();
  if (!id) throw new Error("No sé qué formulario es: pega su enlace de edición en URL_EDICION (arriba) y vuelve a ejecutar.");
  var f = FormApp.openById(id);
  var items = f.getItems(FormApp.ItemType.CHECKBOX);
  var grupos = [["géneros", DATOS.generos], ["temáticas", DATOS.tematicas], ["avisos", DATOS.avisos]];
  var cambiados = 0, faltan = [];
  grupos.forEach(function (par) {
    par[1].forEach(function (g) {
      var item = items.filter(function (it) { return it.getTitle() === g.titulo; })[0];
      if (!item) { faltan.push(g.titulo); return; }
      var cb = item.asCheckboxItem();
      cb.setChoiceValues(g.opciones);
      if (g.rango) cb.setHelpText(cb.getHelpText().replace(/de «.*» a «.*»/, g.rango));
      cambiados++;
    });
  });
  Logger.log("Listas actualizadas: " + cambiados + " preguntas.");
  if (faltan.length) throw new Error("No encuentro estas preguntas en el formulario: " + faltan.join(", ") +
    ". No se ha cambiado su lista; avisa a Claude.");
}

var URL_LISTAS = "https://www.lasafoteca.com/data/formulario.json";
var CLAVE_HUELLA = "HUELLA_LISTAS";

/** Lee las listas que publica la web y, si han cambiado desde la última vez, actualiza el formulario. */
function sincronizarListas() {
  var r = UrlFetchApp.fetch(URL_LISTAS + "?t=" + Date.now(), { muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) throw new Error("La web no devuelve las listas (HTTP " + r.getResponseCode() + ")");
  var web = JSON.parse(r.getContentText());
  if (!web.google || !web.google.tematicas) throw new Error("formulario.json no trae la parte «google»: avisa a Claude.");
  var texto = JSON.stringify(web.google);
  var huella = Utilities.base64Encode(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, texto, Utilities.Charset.UTF_8));
  var props = PropertiesService.getScriptProperties();
  if (props.getProperty(CLAVE_HUELLA) === huella) { Logger.log("Las listas no han cambiado: nada que hacer."); return; }
  actualizarListas(web.google);
  props.setProperty(CLAVE_HUELLA, huella);
  var n = function (gs) { return gs.reduce(function (s, g) { return s + g.opciones.length; }, 0); };
  Logger.log("Formulario al día: " + n(web.google.generos) + " géneros, " + n(web.google.tematicas) + " temáticas, " +
    n(web.google.avisos) + " avisos.");
}

/** Ejecútala UNA vez: programa sincronizarListas cada noche (entre las 3 y las 4) y la lanza ya. */
function instalarSincronizacionDiaria() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === "sincronizarListas") ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger("sincronizarListas").timeBased().everyDays(1).atHour(3).create();
  Logger.log("Programado: cada noche entre las 3 y las 4.");
  sincronizarListas();
}
