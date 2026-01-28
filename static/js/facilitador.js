console.log("facilitador.js cargado ✅");

(() => {
  const baseUrl = "/facilitador/ajax/personas-cedula/"; // ✅ coincide con tu urls.py

  const input = document.getElementById("cedulaSearchFac");
  const resultsBox = document.getElementById("cedulaResultsFac");

  const hidden = document.getElementById("personaIdHiddenFac");

  const vId = document.getElementById("persona_id_fac");
  const vNombre = document.getElementById("persona_nombre_fac");
  const vApellido = document.getElementById("persona_apellido_fac");
  const vCedula = document.getElementById("persona_cedula_fac");

  if (!input || !resultsBox || !hidden || !vId || !vNombre || !vApellido || !vCedula) return;

  let timer = null;

  const hide = () => {
    resultsBox.style.display = "none";
    resultsBox.innerHTML = "";
  };

  const show = () => {
    resultsBox.style.display = "block";
  };

  const clearVisuals = () => {
    hidden.value = "";
    vId.value = "";
    vNombre.value = "";
    vApellido.value = "";
    vCedula.value = "";
  };

  const setPersona = (p) => {
    hidden.value = p.id;
    vId.value = p.id;
    vNombre.value = p.nombre || "";
    vApellido.value = p.apellido || "";
    vCedula.value = p.cedula || "";
    input.value = p.cedula || "";
  };

  const render = (items) => {
    resultsBox.innerHTML = "";

    if (!items || items.length === 0) {
      resultsBox.innerHTML = `<div class="list-group-item text-muted">Sin resultados</div>`;
      show();
      return;
    }

    items.forEach((p) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "list-group-item list-group-item-action";
      btn.innerHTML = `<strong>${p.cedula}</strong> — ${p.nombre} ${p.apellido}`;
      btn.addEventListener("click", () => {
        setPersona(p);
        hide();
      });
      resultsBox.appendChild(btn);
    });

    show();
  };

  const search = async (q) => {
    const resp = await fetch(`${baseUrl}?q=${encodeURIComponent(q)}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    return data.resultados || [];
  };

  input.addEventListener("input", () => {
    const q = (input.value || "").trim();
    clearVisuals();

    if (q.length < 5) {
      hide();
      return;
    }

    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const items = await search(q);
        render(items);
      } catch (e) {
        resultsBox.innerHTML = `<div class="list-group-item text-danger">No se pudo buscar.</div>`;
        show();
      }
    }, 250);
  });

  document.addEventListener("click", (e) => {
    if (!resultsBox.contains(e.target) && e.target !== input) hide();
  });

  hide();
})();
