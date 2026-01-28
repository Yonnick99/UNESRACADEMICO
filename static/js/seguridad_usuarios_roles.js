console.log("seguridad_usuarios_roles.js cargado ✅");

(function () {
  const input = document.getElementById("cedulaSearchSeg");
  const results = document.getElementById("cedulaResultsSeg");
  const btn = document.getElementById("btnCargarPersonaSeg");
  const hidden = document.getElementById("personaIdHiddenSeg");

  const idOut = document.getElementById("persona_id_seg");
  const nomOut = document.getElementById("persona_nombre_seg");
  const apeOut = document.getElementById("persona_apellido_seg");
  const cedOut = document.getElementById("persona_cedula_seg");

  if (!input || !results || !btn || !hidden) return;

  let selected = null;
  let timer = null;

  function clearSelection() {
    selected = null;
    hidden.value = "";
    btn.disabled = true;
    idOut.value = "";
    nomOut.value = "";
    apeOut.value = "";
    cedOut.value = "";
  }

  function showResults(items) {
    results.innerHTML = "";
    if (!items.length) {
      results.style.display = "none";
      return;
    }
    items.forEach(p => {
      const a = document.createElement("button");
      a.type = "button";
      a.className = "list-group-item list-group-item-action";
      a.textContent = `${p.cedula} — ${p.nombre} ${p.apellido}`;
      a.addEventListener("click", () => {
        selected = p;
        hidden.value = p.id_persona;

        // visual
        idOut.value = p.id_persona;
        nomOut.value = p.nombre;
        apeOut.value = p.apellido;
        cedOut.value = p.cedula;

        btn.disabled = false;
        results.style.display = "none";
      });
      results.appendChild(a);
    });
    results.style.display = "block";
  }

  input.addEventListener("input", () => {
    const q = (input.value || "").trim();
    clearTimeout(timer);

    if (!/^\d+$/.test(q) || q.length < 5) {
      results.style.display = "none";
      clearSelection();
      return;
    }

    timer = setTimeout(async () => {
      try {
        const resp = await fetch(`/seguridad/ajax/personas-cedula/?q=${encodeURIComponent(q)}`, {
          headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        const data = await resp.json();
        showResults(data.resultados || []);
      } catch (e) {
        results.style.display = "none";
        clearSelection();
      }
    }, 250);
  });

  btn.addEventListener("click", () => {
    if (!hidden.value) return;
    // recarga la página, ahora con persona_id para que el view pinte el user y roles
    window.location.href = `/seguridad/usuarios/roles/?persona_id=${encodeURIComponent(hidden.value)}`;
  });

  document.addEventListener("click", (e) => {
    if (!results.contains(e.target) && e.target !== input) {
      results.style.display = "none";
    }
  });
})();
