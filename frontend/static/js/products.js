const ProductManagement = {
    products: [],

    init() {
        this.loadProducts();
        this.setupEventListeners();
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
        const openBtn = document.getElementById('manage-products-btn');
        const addBtn = document.getElementById('add-product-btn');
        
        if (openBtn) {
            openBtn.onclick = () => {
                document.getElementById('products-modal').classList.remove('hidden');
                this.loadProducts();
            };
        }

        if (addBtn) {
            addBtn.onclick = async () => {
                const name = document.getElementById('new-product-name').value.trim();
                const desc = document.getElementById('new-product-desc').value.trim();

                if (!name) {
                    alert("Please enter a product name.");
                    return;
                }

                const formData = new FormData();
                formData.append('name', name);
                formData.append('description', desc);

                try {
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
                        await this.loadProducts();
                    } else {
                        Toast.show("Failed to add product", "error");
                    }
                } catch (e) {
                    console.error(e);
                    Toast.show("Error adding product", "error");
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

        list.innerHTML = this.products.map(p => `
            <div class="account-item">
                <div class="account-info">
                    <strong>${p.name}</strong>
                    <span style="display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden;">${p.description || ''}</span>
                </div>
                <button class="btn-icon delete" onclick="ProductManagement.deleteProduct(${p.id})">✕</button>
            </div>
        `).join('');
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
