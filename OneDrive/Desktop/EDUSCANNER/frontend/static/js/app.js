"use strict";

/**
 * EDUSCANNER
 * Core UI
 */

(() => {

    const sidebar = document.getElementById("sidebar");
    const sidebarOpen = document.getElementById("sidebarOpen");
    const sidebarClose = document.getElementById("sidebarClose");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    if (!sidebar) {
        return;
    }


    function openSidebar() {

        sidebar.classList.add("open");

        sidebarOverlay?.classList.add("active");

        sidebarOverlay?.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.style.overflow = "hidden";
    }


    function closeSidebar() {

        sidebar.classList.remove("open");

        sidebarOverlay?.classList.remove("active");

        sidebarOverlay?.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.style.overflow = "";
    }


    sidebarOpen?.addEventListener(
        "click",
        openSidebar
    );


    sidebarClose?.addEventListener(
        "click",
        closeSidebar
    );


    sidebarOverlay?.addEventListener(
        "click",
        closeSidebar
    );


    document.addEventListener(
        "keydown",
        (event) => {

            if (event.key === "Escape") {
                closeSidebar();
            }

        }
    );


    /*
     * Ao voltar para desktop, garante que o estado mobile
     * não permaneça preso.
     */

    window.addEventListener(
        "resize",
        () => {

            if (window.innerWidth > 900) {
                closeSidebar();
            }

        },
        { passive: true }
    );

})();
const app = document.querySelector("#app");

function render() {
    app.innerHTML = `
        <main class="app-shell">

            <section class="welcome">
                <span class="brand">EDUSCANNER</span>

                <h1>
                    Correção inteligente
                    de cartões-resposta.
                </h1>

                <p>
                    Gerencie turmas, cartões-resposta
                    e correções em um único lugar.
                </p>

                <div class="quick-actions">

                    <button
                        type="button"
                        data-action="scanner"
                    >
                        Scanner
                    </button>

                    <button
                        type="button"
                        data-action="classes"
                    >
                        Turmas
                    </button>

                    <button
                        type="button"
                        data-action="cards"
                    >
                        Cartões-resposta
                    </button>

                </div>

            </section>

        </main>
    `;

    bindEvents();
}


function bindEvents() {
    document
        .querySelectorAll("[data-action]")
        .forEach((button) => {

            button.addEventListener("click", () => {
                const action = button.dataset.action;

                console.log(
                    `EDUSCANNER → ação: ${action}`
                );
            });
        });
}


render();