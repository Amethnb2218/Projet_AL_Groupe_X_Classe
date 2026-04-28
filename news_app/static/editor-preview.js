(function () {
    function bindImagePreview(input) {
        const form = input.closest("form");
        if (!form || !window.URL || !window.URL.createObjectURL) {
            return;
        }

        const image = form.querySelector("[data-image-preview-img]");
        const preview = form.querySelector("[data-image-preview]");
        const removeInput = form.querySelector("[data-image-remove]");
        if (!image) {
            return;
        }

        const originalSrc = image.getAttribute("src");
        const startsEmpty = preview && preview.dataset.empty === "true";
        let objectUrl = null;

        function resetPreview() {
            image.setAttribute("src", originalSrc);
            if (preview) {
                preview.classList.remove("is-updated");
                preview.classList.toggle("is-empty", startsEmpty);
            }
        }

        input.addEventListener("change", function () {
            if (objectUrl) {
                window.URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }

            const file = input.files && input.files[0];
            if (!file) {
                resetPreview();
                return;
            }

            if (!file.type || !file.type.startsWith("image/")) {
                return;
            }

            objectUrl = window.URL.createObjectURL(file);
            image.setAttribute("src", objectUrl);
            if (preview) {
                preview.classList.add("is-updated");
                preview.classList.remove("is-empty");
            }
            if (removeInput) {
                removeInput.checked = false;
            }
        });

        if (removeInput) {
            removeInput.addEventListener("change", function () {
                if (removeInput.checked && !input.files.length) {
                    image.setAttribute("src", originalSrc);
                    if (preview) {
                        preview.classList.remove("is-updated");
                        preview.classList.add("is-empty");
                    }
                } else if (!removeInput.checked && !input.files.length) {
                    resetPreview();
                }
            });
        }
    }

    document.querySelectorAll("[data-image-input]").forEach(bindImagePreview);
})();
