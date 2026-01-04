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
                const styleSelect = document.getElementById('style-select');
                const paletteSelect = document.getElementById('palette-select');
                
                if (!styleSelect || !paletteSelect) return;

                const style = styleSelect.value;
                const palette = paletteSelect.value;

                this.modal.classList.add('hidden');
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
