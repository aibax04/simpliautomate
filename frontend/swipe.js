class SwipeApp {
    constructor() {
        this.stack = document.getElementById('card-stack');
        this.prefModal = document.getElementById('pref-modal');
        this.resultModal = document.getElementById('result-modal');
        this.cards = [];
        this.currentNews = null;

        this.init();
        this.bindGlobalEvents();
    }

    async init() {
        const news = await Api.fetchNews();
        this.stack.innerHTML = '';
        if (news.length === 0) {
            this.stack.innerHTML = '<p>No news found for today.</p>';
            return;
        }

        news.forEach((item, index) => {
            this.createCard(item, index);
        });
        this.renderStack();
    }

    createCard(data, index) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.backgroundColor = data.palette.bg;
        card.style.borderTop = `6px solid ${data.palette.accent}`;

        card.innerHTML = `
            <div class="category" style="color: ${data.palette.accent}">${data.category}</div>
            <h2 style="color: ${data.palette.text}">${data.headline}</h2>
            <div class="content">${data.context}</div>
            <div class="footer">
                <span>${data.source}</span>
                <span>${new Date().toLocaleDateString()}</span>
            </div>
        `;

        this.bindSwipe(card, data);
        this.stack.appendChild(card);
        this.cards.push(card);
    }

    bindSwipe(card, data) {
        let startX, startY, moveX, moveY;
        let isDragging = false;

        const onStart = (e) => {
            isDragging = true;
            startX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
            startY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
            card.style.transition = 'none';
        };

        const onMove = (e) => {
            if (!isDragging) return;
            moveX = (e.type.includes('touch') ? e.touches[0].clientX : e.clientX) - startX;
            moveY = (e.type.includes('touch') ? e.touches[0].clientY : e.clientY) - startY;

            const rotation = moveX / 10;
            card.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${rotation}deg)`;
        };

        const onEnd = () => {
            if (!isDragging) return;
            isDragging = false;
            card.style.transition = 'transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';

            if (Math.abs(moveX) > 120) {
                if (moveX > 0) this.handleRightSwipe(card, data);
                else this.handleLeftSwipe(card);
            } else {
                card.style.transform = '';
                this.renderStack();
            }
            moveX = moveY = 0;
        };

        card.addEventListener('mousedown', onStart);
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onEnd);

        card.addEventListener('touchstart', onStart);
        card.addEventListener('touchmove', onMove);
        card.addEventListener('touchend', onEnd);
    }

    handleLeftSwipe(card) {
        card.style.transform = 'translateX(-1000px) rotate(-30deg)';
        card.style.opacity = '0';
        this.popCard();
    }

    handleRightSwipe(card, data) {
        card.style.transform = 'translateX(1000px) rotate(30deg)';
        card.style.opacity = '0';
        this.currentNews = data;
        this.showPrefs();
        this.popCard();
    }

    popCard() {
        const card = this.cards.shift();
        setTimeout(() => {
            card.remove();
            if (this.cards.length === 0) this.init(); // Refetch if empty
            else this.renderStack();
        }, 300);
    }

    renderStack() {
        this.cards.forEach((card, i) => {
            card.style.zIndex = this.cards.length - i;
            card.style.transform = `scale(${1 - i * 0.05}) translateY(${i * 15}px)`;
            card.style.opacity = i > 2 ? 0 : 1;
        });
    }

    showPrefs() {
        this.prefModal.classList.remove('hidden');
    }

    bindGlobalEvents() {
        document.getElementById('close-modal').onclick = () => {
            this.prefModal.classList.add('hidden');
        };

        document.getElementById('generate-btn').onclick = async () => {
            const status = document.getElementById('generation-status');
            status.classList.remove('hidden');

            const prefs = {
                tone: document.getElementById('tone-select').value,
                audience: document.getElementById('audience-select').value,
                length: document.getElementById('length-select').value
            };

            const result = await Api.generatePost(this.currentNews, prefs);

            status.classList.add('hidden');
            this.prefModal.classList.add('hidden');

            document.getElementById('post-preview').innerText = result.content;
            this.resultModal.classList.remove('hidden');
        };

        document.getElementById('publish-btn').onclick = async () => {
            const content = document.getElementById('post-preview').innerText;
            const res = await Api.publishPost(content);
            alert(res.message || "Post successful!");
            this.resultModal.classList.add('hidden');
        };

        document.getElementById('edit-btn').onclick = () => {
            this.resultModal.classList.add('hidden');
            this.prefModal.classList.remove('hidden');
        };

        // Manual controls
        document.getElementById('skip-btn').onclick = () => {
            if (this.cards.length) this.handleLeftSwipe(this.cards[0]);
        };
        document.getElementById('approve-btn').onclick = () => {
            if (this.cards.length) this.handleRightSwipe(this.cards[0], this.currentNews); // This is simplified
        };
    }

    injectCards(newCards) {
        if (!newCards || newCards.length === 0) return;

        // Remove "No news" message if present
        if (this.stack.innerHTML.includes('No news')) {
            this.stack.innerHTML = '';
        }

        newCards.forEach((item, index) => {
            // Add on top of existing or end (here we stick to simple push and re-render logic if needed, 
            // but createCard appends to stack. We might want them on TOP? 
            // Swipe stack usually works LIFO or FIFO depending on z-index.
            // createCard -> pushes to this.cards, appends to DOM.
            // renderStack -> sets z-index based on position in array. 
            // To make them appear "next", we should probably unshift or just push.
            // If we push, they are at the bottom. To make them immediate, unshift?
            // createCard appends to DOM (bottom visually, but top in z-order? No, renderStack controls z-index).
            // renderStack: i=0 is top.

            // So if we want them to show UP, we should put them at the start of the array.
            // But createCard appends to DOM.
            // Let's create element, prepend to stack?

            const card = document.createElement('div');
            card.className = 'card';
            card.style.backgroundColor = item.palette.bg;
            card.style.borderTop = `6px solid ${item.palette.accent}`;

            card.innerHTML = `
                <div class="category" style="color: ${item.palette.accent}">${item.category}</div>
                <h2 style="color: ${item.palette.text}">${item.headline}</h2>
                <div class="content">${item.context}</div>
                <div class="footer">
                    <span>${item.source}</span>
                    <span>${new Date().toLocaleDateString()}</span>
                </div>
            `;

            this.bindSwipe(card, item);

            // Add to FRONT of array/stack so they are seen first
            this.cards.unshift(card);
            this.stack.insertBefore(card, this.stack.firstChild);
            // Note: If renderStack relies on array order, this ensures index 0 is this new card.
        });

        this.renderStack();
    }
}

window.onload = () => {
    window.app = new SwipeApp();
};
