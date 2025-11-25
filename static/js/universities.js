// Universities page JavaScript

let currentPage = 1;
let currentSearch = '';
let currentState = '';

// Load states on page load
document.addEventListener('DOMContentLoaded', function() {
    loadStates();
    searchUniversities();
    
    // Handle Enter key in search
    const searchInput = document.getElementById('searchQuery');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchUniversities();
            }
        });
    }
});

async function loadStates() {
    try {
        const data = await apiGet('/universities/states');
        const stateFilter = document.getElementById('stateFilter');
        if (stateFilter && data.states) {
            data.states.forEach(state => {
                const option = document.createElement('option');
                option.value = state;
                option.textContent = state;
                stateFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading states:', error);
    }
}

async function searchUniversities(page = 1) {
    currentPage = page;
    currentSearch = document.getElementById('searchQuery')?.value || '';
    currentState = document.getElementById('stateFilter')?.value || '';
    
    const container = document.getElementById('universitiesContainer');
    const loading = document.getElementById('loadingIndicator');
    
    if (loading) loading.classList.remove('d-none');
    
    try {
        const params = new URLSearchParams({
            page: page,
            limit: 20
        });
        if (currentSearch) params.append('q', currentSearch);
        if (currentState) params.append('state', currentState);
        
        const data = await apiGet(`/universities?${params}`);
        
        if (container) {
            if (data.universities && data.universities.length > 0) {
                container.innerHTML = data.universities.map(uni => `
                    <div class="card university-card mb-3">
                        <div class="card-body">
                            <h5 class="card-title">${uni.name || 'Unknown University'}</h5>
                            <p class="card-text">
                                <strong>State:</strong> ${uni['state-province'] || 'Not specified'}<br>
                                ${uni.web_pages && uni.web_pages.length > 0 ? 
                                    `<a href="${uni.web_pages[0]}" target="_blank">${uni.web_pages[0]}</a>` : ''}
                            </p>
                            <a href="/universities/${uni._id}" class="btn btn-primary">View Details</a>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<div class="alert alert-info">No universities found.</div>';
            }
        }
        
        renderPagination(data.pagination);
        
    } catch (error) {
        showError('Failed to load universities: ' + error.message);
        if (container) container.innerHTML = '<div class="alert alert-danger">Error loading universities.</div>';
    } finally {
        if (loading) loading.classList.add('d-none');
    }
}

function renderPagination(pagination) {
    const container = document.getElementById('paginationContainer');
    if (!container || !pagination) return;
    
    if (pagination.pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<nav><ul class="pagination justify-content-center">';
    
    // Previous button
    html += `<li class="page-item ${pagination.page === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="searchUniversities(${pagination.page - 1}); return false;">Previous</a>
    </li>`;
    
    // Page numbers
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === 1 || i === pagination.pages || (i >= pagination.page - 2 && i <= pagination.page + 2)) {
            html += `<li class="page-item ${i === pagination.page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="searchUniversities(${i}); return false;">${i}</a>
            </li>`;
        } else if (i === pagination.page - 3 || i === pagination.page + 3) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    // Next button
    html += `<li class="page-item ${pagination.page === pagination.pages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="searchUniversities(${pagination.page + 1}); return false;">Next</a>
    </li>`;
    
    html += '</ul></nav>';
    container.innerHTML = html;
}

// For university detail page
if (window.location.pathname.includes('/universities/')) {
    const universityId = window.location.pathname.split('/universities/')[1].split('/')[0];
    loadUniversityDetail(universityId);
}

async function loadUniversityDetail(universityId) {
    const container = document.getElementById('universityContainer');
    if (!container) return;
    
    try {
        const data = await apiGet(`/universities/${universityId}`);
        const uni = data;
        
        container.innerHTML = `
            <div class="card">
                <div class="card-body">
                    <h1>${uni.name || 'Unknown University'}</h1>
                    <p><strong>State:</strong> ${uni['state-province'] || 'Not specified'}</p>
                    ${uni.web_pages && uni.web_pages.length > 0 ? 
                        `<p><strong>Website:</strong> <a href="${uni.web_pages[0]}" target="_blank">${uni.web_pages[0]}</a></p>` : ''}
                    ${uni.domains && uni.domains.length > 0 ? 
                        `<p><strong>Domains:</strong> ${uni.domains.join(', ')}</p>` : ''}
                    
                    ${uni.related_programmes && uni.related_programmes.length > 0 ? `
                        <hr>
                        <h3>Related Programmes</h3>
                        <div class="list-group">
                            ${uni.related_programmes.map(prog => `
                                <a href="/programmes" class="list-group-item list-group-item-action">
                                    ${prog.title || 'Unknown Programme'} - ${prog.degree_type || ''}
                                </a>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    } catch (error) {
        container.innerHTML = '<div class="alert alert-danger">Error loading university details.</div>';
        console.error('Error loading university:', error);
    }
}

