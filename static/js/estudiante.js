(function () {
  const selCarrera = document.getElementById("id_id_carrera");
  const selMencion = document.getElementById("id_id_mencion");

  if (!selCarrera || !selMencion) return;

  // URL base del endpoint (la completamos con el carrera_id)
  const baseUrl = "/participante/ajax/menciones/";

  function setLoadingState() {
    selMencion.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "Cargando menciones...";
    selMencion.appendChild(opt);
    selMencion.disabled = true;
  }

  function setEmptyState(msg) {
    selMencion.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = msg || "Seleccione una carrera primero";
    selMencion.appendChild(opt);
    selMencion.disabled = true;
  }

  function setOptions(items, selectedValue) {
    selMencion.innerHTML = "";

    const opt0 = document.createElement("option");
    opt0.value = "";
    opt0.textContent = "Seleccione una mención...";
    selMencion.appendChild(opt0);

    items.forEach((it) => {
      const opt = document.createElement("option");
      opt.value = it.id_mencion;
      opt.textContent = it.nombre;
      if (selectedValue && String(selectedValue) === String(it.id_mencion)) {
        opt.selected = true;
      }
      selMencion.appendChild(opt);
    });

    selMencion.disabled = false;
  }

  async function cargarMenciones(carreraId, selectedValue = null) {
    if (!carreraId) {
      setEmptyState("Seleccione una carrera primero");
      return;
    }

    setLoadingState();

    try {
      const resp = await fetch(`${baseUrl}${carreraId}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      if (!resp.ok) {
        setEmptyState("No se pudo cargar menciones");
        return;
      }

      const data = await resp.json();
      const results = data.results || [];

      if (!results.length) {
        setEmptyState("Esta carrera no tiene menciones");
        return;
      }

      setOptions(results, selectedValue);
    } catch (e) {
      setEmptyState("Error de conexión");
    }
  }

  // Al cambiar carrera, recargar menciones
  selCarrera.addEventListener("change", () => {
    cargarMenciones(selCarrera.value);
  });

  // Estado inicial:
  // - si ya hay carrera seleccionada (por ejemplo al volver con errores), cargamos menciones
  // - y tratamos de respetar la mención ya seleccionada
  const carreraInicial = selCarrera.value;
  const mencionInicial = selMencion.value;

  if (carreraInicial) {
    cargarMenciones(carreraInicial, mencionInicial);
  } else {
    setEmptyState("Seleccione una carrera primero");
  }
})();
