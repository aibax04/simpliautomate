const ProductManagement = {
    products: [],

    init() {
        this.loadProducts();
        this.setupEventListeners();
    },

    showModal() {
        const modal = document.getElementById('products-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.loadProducts();
        }
    },

    async loadProducts() {
        try {
            const response = await fetch('/api/products', {
                headers: Api.getHeaders()
            });
            this.products = await response.json();
            this.renderProducts();
            this.updateSelectors();
        } catch (e) {
            console.error("Failed to load products:", e);
        }
    },

    setupEventListeners() {
        const addBtn = document.getElementById('add-product-btn');
        
        if (addBtn) {
            addBtn.onclick = async () => {
                const name = document.getElementById('new-product-name').value.trim();
                const desc = document.getElementById('new-product-desc').value.trim();
                const url = document.getElementById('new-product-url').value.trim();
                const docFiles = document.getElementById('new-product-docs').files;
                const photoFiles = document.getElementById('new-product-photos').files;

                if (!name) {
                    Toast.show("Please enter a product name.", "error");
                    return;
                }

                const formData = new FormData();
                formData.append('name', name);
                formData.append('description', desc);
                formData.append('website_url', url);
                
                for (let i = 0; i < docFiles.length; i++) {
                    formData.append('documents', docFiles[i]);
                }
                for (let i = 0; i < photoFiles.length; i++) {
                    formData.append('photos', photoFiles[i]);
                }

                try {
                    addBtn.disabled = true;
                    addBtn.innerText = "Creating...";
                    
                    const response = await fetch('/api/products', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('simplii_token')}`
                        },
                        body: formData
                    });

                    if (response.ok) {
                        Toast.show("Product added successfully!");
                        document.getElementById('new-product-name').value = '';
                        document.getElementById('new-product-desc').value = '';
                        document.getElementById('new-product-url').value = '';
                        document.getElementById('new-product-docs').value = '';
                        document.getElementById('new-product-photos').value = '';
                        await this.loadProducts();
                    } else {
                        Toast.show("Failed to add product", "error");
                    }
                } catch (e) {
                    console.error(e);
                    Toast.show("Error adding product", "error");
                } finally {
                    addBtn.disabled = false;
                    addBtn.innerText = "Create Product";
                }
            };
        }
    },

    renderProducts() {
        const list = document.getElementById('product-list');
        if (!list) return;

        if (this.products.length === 0) {
            list.innerHTML = '<p style="text-align:center; padding: 20px; color: var(--text-secondary);">No products added yet.</p>';
            return;
        }

        list.innerHTML = this.products.map(p => {
            const docs = (p.collateral || []).filter(c => c.file_type === 'document').length;
            const photos = (p.collateral || []).filter(c => c.file_type === 'photo').length;
            
            return `
                <div class="account-item" style="flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px;">
                    <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                        <strong>${p.name}</strong>
                        <button class="btn-icon delete" onclick="ProductManagement.deleteProduct(${p.id})">✕</button>
                    </div>
                    <span style="font-size: 13px; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-top: 2px;">
                        ${p.description || 'No description'}
                    </span>
                    ${p.website_url ? `<a href="${p.website_url}" target="_blank" style="font-size: 11px; color: var(--accent); text-decoration: none; margin-top: 2px;">${p.website_url}</a>` : ''}
                    <div style="display: flex; gap: 10px; margin-top: 6px;">
                        ${docs > 0 ? `<span style="font-size: 11px; background: var(--bg); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border);">DOCS: ${docs}</span>` : ''}
                        ${photos > 0 ? `<span style="font-size: 11px; background: var(--bg); padding: 2px 6px; border-radius: 4px; border: 1px solid var(--border);">PHOTOS: ${photos}</span>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    },

    async deleteProduct(id) {
        if (!confirm("Are you sure you want to delete this product?")) return;

        try {
            const response = await fetch(`/api/products/${id}`, {
                method: 'DELETE',
                headers: Api.getHeaders()
            });

            if (response.ok) {
                Toast.show("Product deleted");
                await this.loadProducts();
            }
        } catch (e) {
            console.error(e);
            Toast.show("Failed to delete", "error");
        }
    },

    updateSelectors() {
        const selectors = document.querySelectorAll('.product-selector');
        selectors.forEach(select => {
            const currentValue = select.value;
            select.innerHTML = '<option value="">None (Generic Industry News)</option>' + 
                this.products.map(p => `
                    <option value="${p.id}" ${p.id == currentValue ? 'selected' : ''}>
                        ${p.name}
                    </option>
                `).join('');
        });
    }
};

document.addEventListener('DOMContentLoaded', () => ProductManagement.init());
