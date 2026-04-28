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
        let objectUrl = null;

        input.addEventListener("change", function () {
            if (objectUrl) {
                window.URL.revokeObjectURL(objectUrl);
                objectUrl = null;
            }

            const file = input.files && input.files[0];
            if (!file) {
                image.setAttribute("src", originalSrc);
                preview && preview.classList.remove("is-updated");
                return;
            }

            if (!file.type || !file.type.startsWith("image/")) {
                return;
            }

            objectUrl = window.URL.createObjectURL(file);
            image.setAttribute("src", objectUrl);
            preview && preview.classList.add("is-updated");
            if (removeInput) {
                removeInput.checked = false;
            }
        });

        if (removeInput) {
            removeInput.addEventListener("change", function () {
                if (removeInput.checked && !input.files.length) {
                    image.setAttribute("src", originalSrc);
                    preview && preview.classList.remove("is-updated");
                }
            });
        }
    }

    document.querySelectorAll("[data-image-input]").forEach(bindImagePreview);
})();
