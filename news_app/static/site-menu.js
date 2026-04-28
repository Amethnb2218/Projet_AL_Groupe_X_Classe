(function () {
    const header = document.querySelector("[data-site-header]");
    const toggle = document.querySelector("[data-menu-toggle]");
    const mobileQuery = window.matchMedia("(max-width: 820px)");

    if (!header || !toggle) {
        return;
    }

    function setOpen(open) {
        header.classList.toggle("is-menu-open", open);
        toggle.setAttribute("aria-expanded", String(open));
        toggle.setAttribute("aria-label", open ? "Fermer le menu" : "Ouvrir le menu");
    }

    toggle.addEventListener("click", function () {
        setOpen(!header.classList.contains("is-menu-open"));
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            setOpen(false);
        }
    });

    header.querySelectorAll(".main-nav a, .session a, .session button").forEach(function (item) {
        item.addEventListener("click", function () {
            if (mobileQuery.matches) {
                setOpen(false);
            }
        });
    });

    window.addEventListener("resize", function () {
        if (!mobileQuery.matches) {
            setOpen(false);
        }
    });
})();
