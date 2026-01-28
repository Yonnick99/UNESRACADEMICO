(function () {
  const sidebar = document.getElementById("sidebar");
  const btn = document.getElementById("btnToggleSidebar");
  const STORAGE_KEY = "unesr_sidebar_collapsed";

  function setCollapsed(collapsed) {
    if (!sidebar) return;
    sidebar.classList.toggle("is-collapsed", collapsed);
    localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
  }

  function getCollapsed() {
    return localStorage.getItem(STORAGE_KEY) === "1";
  }

  function normalizePath(path) {
    if (!path) return "/";
    // Elimina querystring/hash, asegura formato /ruta/
    const clean = path.split("?")[0].split("#")[0];
    if (clean === "") return "/";
    return clean.endsWith("/") ? clean : clean + "/";
  }

  function setActiveMenu() {
    if (!sidebar) return;

    const current = normalizePath(window.location.pathname);

    // Quitamos activos previos (por si cambias contenido vía HTMX/AJAX en el futuro)
    sidebar.querySelectorAll(".nav__item.active, .nav__subitem.active").forEach(el => {
      el.classList.remove("active");
    });

    // Selecciona enlaces navegables
    const links = Array.from(sidebar.querySelectorAll("a.nav__item, a.nav__subitem"))
      .filter(a => a.getAttribute("href") && a.getAttribute("href") !== "#");

    // Determina el mejor match:
    // 1) match exacto por pathname
    // 2) match por prefijo (para secciones tipo /gestion/periodos/...)
    let best = null;
    let bestLen = -1;

    for (const a of links) {
      try {
        const url = new URL(a.getAttribute("href"), window.location.origin);
        const target = normalizePath(url.pathname);

        // exacto
        if (target === current) {
          best = a;
          bestLen = target.length;
          break;
        }

        // prefijo (evita que "/" marque todo)
        if (target !== "/" && current.startsWith(target) && target.length > bestLen) {
          best = a;
          bestLen = target.length;
        }
      } catch (e) {
        // Si el href no es URL válida (raro), se ignora
      }
    }

    if (!best) return;

    best.classList.add("active");

    // Si el link está dentro de un collapse, lo abrimos automáticamente
    const collapseDiv = best.closest(".collapse");
    if (collapseDiv) {
      // Bootstrap collapse usa la clase "show" para estar abierto
      collapseDiv.classList.add("show");

      // Encuentra el botón que controla ese collapse y lo pone aria-expanded="true"
      const controllerBtn = sidebar.querySelector(`[data-bs-target="#${collapseDiv.id}"]`);
      if (controllerBtn) {
        controllerBtn.setAttribute("aria-expanded", "true");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    // Estado inicial del sidebar (persistente)
    setCollapsed(getCollapsed());

    // Marcar activo según URL actual
    setActiveMenu();
  });

  if (btn) {
    btn.addEventListener("click", () => {
      setCollapsed(!sidebar.classList.contains("is-collapsed"));
    });
  }
})();
