// filepath: /C:/PhotoStore/static/js/search.js
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const imageGrid = document.querySelector('.image-grid');
    
    searchInput.addEventListener('input', async function() {
        const searchTerm = this.value.trim();
        
        try {
            const response = await fetch(`/search?term=${encodeURIComponent(searchTerm)}`);
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();

            // Clear existing images
            imageGrid.innerHTML = '';

            // Add filtered images
            data.forEach(image => {
                const imageDiv = document.createElement('div');
                imageDiv.className = 'image-grid-item';
                imageDiv.innerHTML = `
                    <a href="/detail/${image.id}">
                        <img src="/static/uploads/${image.filename}" 
                             alt="${image.filename}"
                             loading="lazy">
                    </a>
                `;
                imageGrid.appendChild(imageDiv);
            });
        } catch (error) {
            console.error('Search error:', error);
        }
    });
});