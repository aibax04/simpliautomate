document.addEventListener('DOMContentLoaded', () => {
    const uploadModal = document.getElementById('upload-modal');
    const openBtn = document.getElementById('upload-main-btn');
    const closeBtn = document.getElementById('close-upload-modal');
    const ingestBtn = document.getElementById('ingest-btn');

    // Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // State
    let activeTab = 'file';

    // 1. Open/Close Modal
    openBtn.addEventListener('click', () => {
        uploadModal.classList.remove('hidden');
    });

    closeBtn.addEventListener('click', () => {
        uploadModal.classList.add('hidden');
        resetForm();
    });

    // 2. Tab Switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all
            tabBtns.forEach(b => {
                b.classList.remove('active');
                b.style.color = ''; // clear inline
            });
            tabContents.forEach(c => c.classList.add('hidden'));

            // Activate clicked
            btn.classList.add('active');

            activeTab = btn.dataset.tab;
            document.getElementById(`tab-${activeTab}`).classList.remove('hidden');
        });
    });

    // 3. Submit
    ingestBtn.addEventListener('click', async () => {
        const status = document.getElementById('ingest-status');
        const fileInput = document.getElementById('file-input');
        const urlInput = document.getElementById('url-input');

        // Validation
        if (activeTab === 'file' && !fileInput.files[0]) {
            alert("Please select a file.");
            return;
        }
        if (activeTab === 'url' && !urlInput.value.trim()) {
            alert("Please enter a URL.");
            return;
        }

        // Show loading
        status.classList.remove('hidden');
        ingestBtn.disabled = true;

        const formData = new FormData();

        if (activeTab === 'file') {
            formData.append('file', fileInput.files[0]);
        } else {
            formData.append('url_data', urlInput.value.trim());
        }

        try {
            const response = await fetch('/api/ingest-source', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Ingestion failed");
            }

            const newCards = await response.json();

            // Inject into SwipeApp
            if (window.app) {
                window.app.injectCards(newCards);
            }

            // Close and reset
            uploadModal.classList.add('hidden');
            resetForm();
            alert(`Found ${newCards.length} relevant news stories based on your source.`);

        } catch (error) {
            alert(`Error: ${error.message}`);
        } finally {
            status.classList.add('hidden');
            ingestBtn.disabled = false;
        }
    });

    function resetForm() {
        document.getElementById('file-input').value = '';
        document.getElementById('url-input').value = '';
    }
});
