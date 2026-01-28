console.log("script.js cargado ✅");

(function () {
  const modalEl = document.getElementById("modalEditar");
  const container = document.getElementById("modal-editar-contenido");

  if (!modalEl || !container) return;

  // =========================
  // Toast rápido (Bootstrap)
  // =========================
  function mostrarToast(mensaje, tipo = "success") {
    // tipo: success | danger | warning | info
    let cont = document.getElementById("toast-container");
    if (!cont) {
      cont = document.createElement("div");
      cont.id = "toast-container";
      cont.className = "toast-container position-fixed top-0 end-0 p-3";
      cont.style.zIndex = "2000";
      document.body.appendChild(cont);
    }

    const toastEl = document.createElement("div");
    toastEl.className = `toast align-items-center text-bg-${tipo} border-0`;
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${mensaje}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button>
      </div>
    `;

    cont.appendChild(toastEl);
    const t = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 1200 });
    t.show();

    toastEl.addEventListener("hidden.bs.toast", () => {
      toastEl.remove();
    });
  }

  function cerrarYRecargarConToast(mensaje, tipo = "success") {
    bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    mostrarToast(mensaje, tipo);

    // pequeño delay para que el usuario vea el toast antes del reload
    setTimeout(() => {
      window.location.reload(); // conserva ?page=...
    }, 650);
  }

  // 1) Cargar el formulario al abrir el modal
  modalEl.addEventListener("show.bs.modal", async (event) => {
    const button = event.relatedTarget;
    const url = button?.getAttribute("data-url");

    if (!url) {
      container.innerHTML =
        "<div class='text-danger'>No se encontró la URL de edición.</div>";
      return;
    }

    container.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-secondary"></div>
      </div>
    `;

    try {
      const resp = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!resp.ok) {
        container.innerHTML = `<div class="text-danger">Error al cargar el formulario (HTTP ${resp.status}).</div>`;
        return;
      }

      const html = await resp.text();
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML =
        "<div class='text-danger'>No se pudo cargar el formulario.</div>";
    }
  });

  // 2) Guardar por AJAX + cerrar modal + recargar manteniendo ?page=
  container.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;

    event.preventDefault();

    const actionUrl = form.getAttribute("action");
    const formData = new FormData(form);

    const submitBtn = form.querySelector("button[type='submit']");
    const originalText = submitBtn ? submitBtn.innerHTML : null;

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = "Guardando...";
    }

    try {
      const resp = await fetch(actionUrl, {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      // Si el servidor redirige (típico en Django al guardar OK),
      // fetch sigue el redirect y devuelve HTML de la lista.
      // Eso lo tratamos como ÉXITO.
      if (resp.redirected || (resp.url && resp.url !== actionUrl)) {
        cerrarYRecargarConToast("Registro actualizado correctamente.", "success");
        return;
      }

      const text = await resp.text();

      // Si devolvió HTML completo (<!DOCTYPE / <html), también es un éxito "implícito"
      // (proviene de redirect o de render completo).
      if (text.includes("<!DOCTYPE") || text.includes("<html")) {
        cerrarYRecargarConToast("Registro actualizado correctamente.", "success");
        return;
      }

      // Si devolvió un <form> asumimos que hay errores y re-renderizamos el parcial
      if (text && text.includes("<form")) {
        container.innerHTML = text;
        return;
      }

      // Si no hay form ni html completo, en éxito cerramos y recargamos
      if (resp.ok) {
        cerrarYRecargarConToast("Registro actualizado correctamente.", "success");
        return;
      }

      container.innerHTML = `<div class="text-danger">Error al guardar (HTTP ${resp.status}).</div>`;

    } catch (err) {
      container.innerHTML =
        "<div class='text-danger'>No se pudo guardar. Revisa tu conexión.</div>";
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText || "Guardar";
      }
    }
  });
})();


// Cambio de componente en pantalla de consulta
(function () {
  const select = document.getElementById("select-consulta");
  if (!select) return;

  select.addEventListener("change", () => {
    const destino = select.value; // ya trae la URL completa por el value del option
    const params = new URLSearchParams(window.location.search);

    // al cambiar de catálogo, reiniciamos página
    params.delete("page");

    const qs = params.toString();
    window.location.href = qs ? `${destino}?${qs}` : destino;
  });
})();


(function () {
  const input = document.getElementById("cedulaSearch");
  const resultsBox = document.getElementById("cedulaResults");
  const btnBuscar = document.getElementById("btnBuscarPersona");

  const hiddenId = document.getElementById("personaIdHidden");
  const outId = document.getElementById("persona_id");
  const outNombre = document.getElementById("persona_nombre");
  const outApellido = document.getElementById("persona_apellido");
  const outCedula = document.getElementById("persona_cedula");

  if (!input || !resultsBox || !btnBuscar || !hiddenId) return;

  let selected = null;
  let timer = null;

  function clearResults() {
    resultsBox.innerHTML = "";
    resultsBox.style.display = "none";
  }

  function setSelected(p) {
    selected = p;
    hiddenId.value = p.id_persona;

    if (outId) outId.value = p.id_persona;
    if (outNombre) outNombre.value = p.nombre || "";
    if (outApellido) outApellido.value = p.apellido || "";
    if (outCedula) outCedula.value = p.cedula || "";

    btnBuscar.disabled = false;
    clearResults();
  }

  async function fetchPersonasByCedula(term) {
    const url = `/participante/personas/buscar-cedula/?cedula=${encodeURIComponent(term)}`;
    const resp = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!resp.ok) return [];
    const data = await resp.json();
    return data.results || [];
  }

  input.addEventListener("input", () => {
    const raw = input.value || "";
    const digits = raw.replace(/\D/g, "");

    // Reiniciar selección
    selected = null;
    hiddenId.value = "";
    btnBuscar.disabled = true;

    // Limpiar campos visuales
    if (outId) outId.value = "";
    if (outNombre) outNombre.value = "";
    if (outApellido) outApellido.value = "";
    if (outCedula) outCedula.value = "";

    if (timer) clearTimeout(timer);

    if (digits.length < 5) {
      clearResults();
      return;
    }

    timer = setTimeout(async () => {
      const results = await fetchPersonasByCedula(digits);

      resultsBox.innerHTML = "";
      if (!results.length) {
        resultsBox.style.display = "none";
        return;
      }

      results.forEach((p) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "list-group-item list-group-item-action";
        item.textContent = `${p.cedula} — ${p.nombre} ${p.apellido} (ID: ${p.id_persona})`;
        item.addEventListener("click", () => setSelected(p));
        resultsBox.appendChild(item);
      });

      resultsBox.style.display = "block";
    }, 250); // debounce
  });

  // Botón "Buscar": como ya cargamos datos al seleccionar,
  // aquí puedes solo reafirmar selección o simplemente ocultar lista.
  btnBuscar.addEventListener("click", () => {
    if (!selected) return;
    // Nada extra necesario porque ya rellenamos al seleccionar
    clearResults();
  });

  // Cerrar lista si clic fuera
  document.addEventListener("click", (e) => {
    if (!resultsBox.contains(e.target) && e.target !== input) clearResults();
  });
})();
