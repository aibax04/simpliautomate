class ImageOptionsModal {
    constructor(onConfirm) {
        this.modal = document.getElementById('image-options-modal');
        this.confirmBtn = document.getElementById('finalize-generate-btn');
        this.closeBtn = document.getElementById('close-image-options');
        this.onConfirm = onConfirm;

        this.init();
    }

    init() {
        if (!this.modal) return;

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => {
                this.modal.classList.add('hidden');
            });
        }

        if (this.confirmBtn) {
            this.confirmBtn.addEventListener('click', () => {
                if (this.confirmBtn.disabled) return;
                this.confirmBtn.disabled = true;

                const styleSelect = document.getElementById('style-select');
                const paletteSelect = document.getElementById('palette-select');

                if (!styleSelect || !paletteSelect) {
                    this.confirmBtn.disabled = false;
                    return;
                }

                const style = styleSelect.value;
                const palette = paletteSelect.value;

                this.modal.classList.add('hidden');

                // Re-enable after a delay or let the caller handle it? 
                // Since modal is hidden, re-enabling is fine for next use.
                setTimeout(() => { this.confirmBtn.disabled = false; }, 1000);

                if (this.onConfirm) {
                    this.onConfirm({ style, palette });
                }
            });
        }
    }

    show() {
        this.modal.classList.remove('hidden');
    }
}

window.ImageOptionsModal = ImageOptionsModal;
