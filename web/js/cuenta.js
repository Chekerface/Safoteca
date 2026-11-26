/* La Safoteca · cuentas (opcional): guardar favoritos y listas con la cuenta de Google.

   Solo se descarga si alguien toca «Entrar con Google» en Ajustes, o si ya había entrado antes en este
   dispositivo. Quien no entra no descarga nada de esto.

   Piezas (todo gratis, plan Spark de Firebase, sin servidores propios ni claves secretas):
     - Firebase Authentication con Google: nos da un identificador anónimo (uid). No guardamos correo ni nombre.
     - Cloud Firestore: un documento por persona con sus favoritos y listas.
     - App Check con reCAPTCHA v3: solo la web de verdad puede leer y escribir (frena robots y abusos).
     - Reglas de seguridad: tools/cuentas/firestore.rules (cada persona solo ve y cambia lo suyo).

   Dónde se guarda (preparado para el futuro; ver retrospectiva técnica, W16):
     entornos/{pro|pre}/usuarias/{uid}/privado/biblioteca   ← favoritos y listas (lo único activo hoy)
     entornos/{pro|pre}/perfiles/{uid}                      ← futuro: alias público para comentarios
     entornos/{pro|pre}/obras/{id}/votos/{uid}              ← futuro: estrellas (una por persona y obra)
     entornos/{pro|pre}/obras/{id}/comentarios/{id}         ← futuro: comentarios

   Sincronización: el dispositivo manda. Cada cambio se guarda en el móvil y, unos segundos después, en la cuenta.
   Al entrar por primera vez en un dispositivo se JUNTAN las dos copias (no se pierde nada). Después, si la copia
   de la cuenta es más nueva (otro dispositivo) y aquí no hay cambios sin subir, se usa la de la cuenta. */

const V = "13.4.0"; // versión fija del SDK de Firebase (gstatic)
const URL_SDK = (m) => `https://www.gstatic.com/firebasejs/${V}/firebase-${m}.js`;

export async function crear(cfg, g) {
  // g: { leer(k, def), escribir(k, v), favs(), listas(), aplicar({favs, listas}), aviso(texto), cambio() }
  const [{ initializeApp }, A, F, C] = await Promise.all([
    import(URL_SDK("app")), import(URL_SDK("auth")), import(URL_SDK("firestore")), import(URL_SDK("app-check")),
  ]);
  const app = initializeApp(cfg.firebase);
  if (cfg.recaptcha) {
    C.initializeAppCheck(app, { provider: new C.ReCaptchaV3Provider(cfg.recaptcha), isTokenAutoRefreshEnabled: true });
  }
  const auth = A.getAuth(app);
  auth.languageCode = "es";
  const db = F.getFirestore(app);
  const entorno = cfg.entorno === "pre" ? "pre" : "pro";
  const ref = (uid) => F.doc(db, "entornos", entorno, "usuarias", uid, "privado", "biblioteca");

  const estado = { usuaria: null, sincronizando: false, ultima: g.leer("cuenta.ultima", null), error: null };
  let temporizador = null;

  // ---------- Juntar copias ----------
  const juntarListas = (a, b) => {
    const porId = new Map(a.map((l) => [l.id, { ...l, obras: [...l.obras] }]));
    b.forEach((l) => {
      const x = porId.get(l.id);
      if (x) l.obras.forEach((o) => { if (!x.obras.includes(o)) x.obras.push(o); });
      else porId.set(l.id, { ...l, obras: [...l.obras] });
    });
    return [...porId.values()];
  };
  const limpias = (listas) => (Array.isArray(listas) ? listas : [])
    .filter((l) => l && typeof l.id === "string" && Array.isArray(l.obras))
    .map((l) => ({ id: l.id.slice(0, 40), nombre: String(l.nombre || "").slice(0, 40), obras: l.obras.filter(Number.isInteger).slice(0, 2000) }))
    .slice(0, 200);

  async function subir(uid) {
    const rev = (g.leer("cuenta.rev", 0) || 0) + 1;
    await F.setDoc(ref(uid), {
      v: 1, rev, favs: [...g.favs()].filter(Number.isInteger).slice(0, 2000), listas: limpias(g.listas()),
      actualizado: F.serverTimestamp(),
    });
    g.escribir("cuenta.rev", rev);
    g.escribir("cuenta.pendiente", false);
    estado.ultima = new Date().toISOString(); g.escribir("cuenta.ultima", estado.ultima);
  }

  async function sincronizar() {
    const u = estado.usuaria; if (!u) return;
    estado.sincronizando = true; estado.error = null; g.cambio();
    try {
      const s = await F.getDoc(ref(u.uid));
      const nube = s.exists() ? s.data() : null;
      const primeraVez = g.leer("cuenta.uid", null) !== u.uid;
      const pendiente = g.leer("cuenta.pendiente", false);
      const revLocal = g.leer("cuenta.rev", 0) || 0;
      if (nube && (primeraVez || (pendiente && nube.rev > revLocal))) {
        // juntar las dos copias
        const favs = new Set([...g.favs(), ...(nube.favs || [])]);
        g.aplicar({ favs, listas: juntarListas(g.listas(), limpias(nube.listas)) });
        g.escribir("cuenta.rev", nube.rev || 0);
        await subir(u.uid);
      } else if (nube && nube.rev > revLocal) {
        // otro dispositivo guardó después: manda la cuenta
        g.aplicar({ favs: new Set(nube.favs || []), listas: limpias(nube.listas) });
        g.escribir("cuenta.rev", nube.rev || 0);
        g.escribir("cuenta.pendiente", false);
        estado.ultima = new Date().toISOString(); g.escribir("cuenta.ultima", estado.ultima);
      } else if (!nube || pendiente || primeraVez) {
        await subir(u.uid);
      } else {
        // ya estaban iguales
        estado.ultima = new Date().toISOString(); g.escribir("cuenta.ultima", estado.ultima);
      }
      g.escribir("cuenta.uid", u.uid);
    } catch (e) {
      estado.error = "No hemos podido sincronizar. Tus favoritos siguen guardados en este dispositivo.";
      console.warn("[cuenta]", e);
    } finally {
      estado.sincronizando = false; g.cambio();
    }
  }

  A.onAuthStateChanged(auth, (u) => {
    const antes = estado.usuaria && estado.usuaria.uid;
    estado.usuaria = u ? { uid: u.uid, nombre: u.displayName || "", foto: u.photoURL || "" } : null;
    g.escribir("cuenta", !!u);
    if (u && u.uid !== antes) sincronizar();
    g.cambio();
  });

  return {
    estado,
    // Ventana emergente de Google. Tiene que abrirse EN EL MISMO TOQUE (sin esperas antes): si no, el móvil la
    // bloquea. Por eso la app descarga Firebase en un primer toque y abre Google en el segundo.
    // No se usa la redirección: con el dominio de Firebase (firebaseapp.com) distinto de lasafoteca.com, los
    // navegadores móviles (Safari, Chrome) pierden la sesión al volver y no se entra.
    entrar() {
      const p = new A.GoogleAuthProvider();
      p.setCustomParameters({ prompt: "select_account" });
      return A.signInWithPopup(auth, p).catch((e) => {
        if (e && (e.code === "auth/popup-closed-by-user" || e.code === "auth/cancelled-popup-request")) return;
        throw e;
      });
    },
    async salir() {
      await A.signOut(auth);
      ["cuenta.uid", "cuenta.rev", "cuenta.pendiente", "cuenta.ultima"].forEach((k) => g.escribir(k, null));
      g.aviso("Has cerrado la sesión. Tus favoritos siguen en este dispositivo.");
    },
    async borrarCuenta() {
      const u = auth.currentUser; if (!u) return;
      await F.deleteDoc(ref(u.uid));
      try { await A.deleteUser(u); }
      catch (e) {
        if (e && e.code === "auth/requires-recent-login") {
          await A.reauthenticateWithPopup(u, new A.GoogleAuthProvider());
          await A.deleteUser(auth.currentUser);
        } else throw e;
      }
      ["cuenta", "cuenta.uid", "cuenta.rev", "cuenta.pendiente", "cuenta.ultima"].forEach((k) => g.escribir(k, null));
      g.aviso("Cuenta borrada. Hemos eliminado tus datos; los favoritos siguen solo en este dispositivo.");
    },
    // La app avisa de cada cambio de favoritos o listas: se sube agrupado, 3 s después del último.
    cambiado() {
      if (!estado.usuaria) return;
      g.escribir("cuenta.pendiente", true);
      clearTimeout(temporizador);
      temporizador = setTimeout(() => sincronizar(), 3000);
    },
    sincronizar,
  };
}
