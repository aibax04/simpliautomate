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

        this.closeBtn.onclick = () => {
            this.modal.classList.add('hidden');
        };

        this.confirmBtn.onclick = () => {
            const style = document.getElementById('style-select').value;
            const palette = document.getElementById('palette-select').value;

            this.modal.classList.add('hidden');
            if (this.onConfirm) {
                this.onConfirm({ style, palette });
            }
        };
    }

    show() {
        this.modal.classList.remove('hidden');
    }
}

window.ImageOptionsModal = ImageOptionsModal;
