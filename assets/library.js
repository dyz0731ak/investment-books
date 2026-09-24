/* Progressive enhancement: all books and links are in the source HTML. */
(() => {
  "use strict";
  document.documentElement.classList.add("js");
  const normalize = (value) =>
    value.normalize("NFKC").toLocaleLowerCase("ja").trim();
  const parameters = () => new URLSearchParams(location.hash.slice(1));
  document.querySelectorAll(".book-search-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const q = form.querySelector("input").value.trim();
      location.href = "/books/" + (q ? "#q=" + encodeURIComponent(q) : "");
    });
  });
  const filters = document.querySelector("[data-shelf-filters]");
  if (filters) {
    const cards = [
      ...document.querySelectorAll("[data-shelf] [data-book-card]"),
    ];
    filters.addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter]");
      if (!button) return;
      filters
        .querySelectorAll("button")
        .forEach((item) =>
          item.setAttribute("aria-pressed", String(item === button)),
        );
      cards.forEach((card) => {
        card.hidden =
          button.dataset.filter !== "all" &&
          !card.dataset.themes.split(" ").includes(button.dataset.filter);
      });
      document.querySelector("[data-shelf-status]").textContent =
        `${cards.filter((card) => !card.hidden).length}冊を表示しています`;
    });
  }
  const catalog = document.querySelector("[data-catalogue]");
  if (catalog) {
    const query = document.querySelector("#catalogue-query");
    const theme = document.querySelector("#catalogue-theme");
    const form = document.querySelector(".catalogue-controls");
    const cards = [...catalog.querySelectorAll("[data-book-card]")];
    const filter = (updateUrl = true) => {
      const terms = normalize(query.value).split(/\s+/).filter(Boolean);
      let count = 0;
      cards.forEach((card) => {
        const matches =
          terms.every((term) =>
            normalize(card.dataset.search).includes(term),
          ) &&
          (theme.value === "all" ||
            card.dataset.themes.split(" ").includes(theme.value));
        card.hidden = !matches;
        if (matches) count++;
      });
      document.querySelector("#catalogue-status").textContent =
        `${cards.length}冊中 ${count}冊を表示しています`;
      document.querySelector("#no-results").hidden = count !== 0;
      if (updateUrl) {
        const params = new URLSearchParams();
        if (query.value.trim()) params.set("q", query.value.trim());
        if (theme.value !== "all") params.set("theme", theme.value);
        history.replaceState(
          null,
          "",
          "/books/" + (params.size ? "#" + params.toString() : ""),
        );
      }
    };
    const readUrl = () => {
      const params = location.hash
        ? parameters()
        : new URLSearchParams(location.search);
      query.value = params.get("q") || "";
      theme.value = [...theme.options].some(
        (o) => o.value === params.get("theme"),
      )
        ? params.get("theme")
        : "all";
      filter(false);
    };
    query.addEventListener("input", () => filter());
    theme.addEventListener("change", () => filter());
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      filter();
    });
    form.addEventListener("reset", () => {
      query.value = "";
      theme.value = "all";
      filter();
    });
    document.querySelector("#clear-search").addEventListener("click", () => {
      form.reset();
      query.focus();
    });
    window.addEventListener("hashchange", readUrl);
    readUrl();
  }
  document.querySelectorAll("img").forEach((img) => {
    const fallback = () => {
      if (
        img.closest(".library-photo") ||
        img.classList.contains("brand-mark") ||
        img.classList.contains("footer-mark")
      )
        return;
      const label = document.createElement("span");
      label.className = "cover-unavailable";
      label.textContent = img.alt.replace(/の表紙$/, "");
      label.setAttribute("role", "img");
      label.setAttribute(
        "aria-label",
        img.alt + "（書影を読み込めませんでした）",
      );
      img.replaceWith(label);
    };
    img.addEventListener("error", fallback, { once: true });
    if (img.complete && !img.naturalWidth) fallback();
  });
  const menu = document.querySelector(".mobile-menu");
  if (menu) {
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        menu.open = false;
        menu.querySelector("summary").focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  }
})();
