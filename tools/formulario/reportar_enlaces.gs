/**
 * La Safoteca · formulario para avisar de enlaces de «dónde ver» que no funcionan.
 *
 * Cómo usarlo (una sola vez):
 *  1. Entra en https://script.google.com con la cuenta de Google del proyecto → Nuevo proyecto.
 *  2. Pega TODO este archivo, guarda y ejecuta la función `crearFormularioReportes` (acepta los permisos).
 *  3. En el «Registro de ejecución» sale un bloque `reporteEnlaces: {...}`. Cópialo en web/config.js
 *     (sustituye la línea `reporteEnlaces: null`), haz commit y fusiona el PR: los botones de aviso
 *     aparecen solos en las fichas.
 *  4. Las respuestas caen en la hoja «La Safoteca · Enlaces reportados». Para procesarlas: Archivo → Descargar → .xlsx
 *     y `python tools/leer_reportes.py enlaces_reportados.xlsx`.
 * El formulario es anónimo: no pide ni guarda el correo de quien avisa.
 */
function crearFormularioReportes() {
  var f = FormApp.create("La Safoteca · Avisar de un enlace roto");
  f.setDescription("Gracias por avisarnos. Los datos de la obra y el enlace ya vienen rellenados; solo tienes que contarnos qué pasa y pulsar Enviar.");
  f.setCollectEmail(false);
  f.setConfirmationMessage("¡Gracias! Revisaremos el enlace.");

  var id = f.addTextItem().setTitle("Id de la obra").setRequired(true);
  var obra = f.addTextItem().setTitle("Obra").setRequired(true);
  var plat = f.addTextItem().setTitle("Plataforma");
  var enlace = f.addTextItem().setTitle("Enlace").setRequired(true);
  f.addMultipleChoiceItem().setTitle("¿Qué pasa con el enlace?").setRequired(true)
    .setChoiceValues(["No abre o da error", "Lleva a otra obra o a la portada", "La obra ya no está en esa plataforma",
                      "No está disponible en mi país", "Otro"]);
  f.addParagraphTextItem().setTitle("Comentario (opcional)")
    .setHelpText("Si conoces el enlace correcto, puedes ponerlo aquí.");

  var hoja = SpreadsheetApp.create("La Safoteca · Enlaces reportados");
  f.setDestination(FormApp.DestinationType.SPREADSHEET, hoja.getId());

  // Enlace de ejemplo rellenado: de ahí se leen los códigos «entry.NNN» de cada pregunta.
  var r = f.createResponse();
  [[id, "ID"], [obra, "OBRA"], [plat, "PLATAFORMA"], [enlace, "ENLACE"]].forEach(function (p) {
    r.withItemResponse(p[0].createResponse(p[1]));
  });
  var url = r.toPrefilledUrl();
  var q = {};
  url.split("?")[1].split("&").forEach(function (kv) { var a = kv.split("="); q[decodeURIComponent(a[1])] = a[0]; });
  var base = f.getPublishedUrl();
  Logger.log("Formulario (editar): " + f.getEditUrl());
  Logger.log("Hoja de respuestas: " + hoja.getUrl());
  Logger.log("Copia esto en web/config.js:\n" +
    '  reporteEnlaces: { url: "' + base + '", campos: { id: "' + q["ID"] + '", obra: "' + q["OBRA"] +
    '", plataforma: "' + q["PLATAFORMA"] + '", enlace: "' + q["ENLACE"] + '" } },');
}
