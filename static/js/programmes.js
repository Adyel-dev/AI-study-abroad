// Programmes page JavaScript

let currentPage = 1;
let filters = {};

document.addEventListener('DOMContentLoaded', function() {
    loadFilters();
    searchProgrammes();
    
    // Handle Enter key
    const searchInput = document.getElementById('programmeSearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchProgrammes();
            }
        });
    }
});

async function loadFilters() {
    try {
        const data = await apiGet('/programmes/filters');
        
        // Degree types
        const degreeFilter = document.getElementById('degreeFilter');
        if (degreeFilter && data.degree_types) {
            data.degree_types.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                degreeFilter.appendChild(option);
            });
        }
        
        // Languages
        const languageFilter = document.getElementById('languageFilter');
        if (languageFilter && data.languages) {
            data.languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = lang;
                languageFilter.appendChild(option);
            });
        }
        
        // Cities
        const cityFilter = document.getElementById('cityFilter');
        if (cityFilter && data.cities) {
            data.cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                cityFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading filters:', error);
    }
}

async function searchProgrammes(page = 1) {
    currentPage = page;
    
    const container = document.getElementById('programmesContainer');
    const loading = document.getElementById('loadingIndicator');
    
    if (loading) loading.classList.remove('d-none');
    
    try {
        filters = {
            q: document.getElementById('programmeSearch')?.value || '',
            degree_type: document.getElementById('degreeFilter')?.value || '',
            language: document.getElementById('languageFilter')?.value || '',
            city: document.getElementById('cityFilter')?.value || ''
        };
        
        const params = new URLSearchParams({
            page: page,
            limit: 20
        });
        Object.keys(filters).forEach(key => {
            if (filters[key]) params.append(key, filters[key]);
        });
        
        const data = await apiGet(`/programmes?${params}`);
        
        if (container) {
            if (data.programmes && data.programmes.length > 0) {
                container.innerHTML = data.programmes.map(prog => `
                    <div class="col-md-6 col-lg-4 mb-4">
                        <div class="card programme-card h-100">
                            <div class="card-body">
                                <h5 class="card-title">${prog.title || 'Unknown Programme'}</h5>
                                <p class="card-text">
                                    <span class="badge bg-primary">${prog.degree_type || ''}</span>
                                    ${prog.language && prog.language.length > 0 ? 
                                        prog.language.map(lang => `<span class="badge bg-secondary ms-1">${lang}</span>`).join('') : ''}
                                </p>
                                <p class="card-text">
                                    <strong>University:</strong> ${prog.university_name || 'Unknown'}<br>
                                    <strong>City:</strong> ${prog.city || 'Not specified'}<br>
                                    ${prog.tuition_fee_eur_per_semester ? 
                                        `<strong>Tuition:</strong> €${prog.tuition_fee_eur_per_semester}/semester<br>` : ''}
                                    ${prog.duration_semesters ? 
                                        `<strong>Duration:</strong> ${prog.duration_semesters} semesters` : ''}
                                </p>
                            </div>
                            <div class="card-footer">
                                ${prog.source_url ? 
                                    `<a href="${prog.source_url}" target="_blank" class="btn btn-sm btn-outline-primary">Learn More</a>` : ''}
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<div class="alert alert-info">No programmes found.</div>';
            }
        }
        
        renderPagination(data.pagination);
        
    } catch (error) {
        showError('Failed to load programmes: ' + error.message);
        if (container) container.innerHTML = '<div class="alert alert-danger">Error loading programmes.</div>';
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
    
    html += `<li class="page-item ${pagination.page === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="searchProgrammes(${pagination.page - 1}); return false;">Previous</a>
    </li>`;
    
    for (let i = 1; i <= pagination.pages; i++) {
        if (i === 1 || i === pagination.pages || (i >= pagination.page - 2 && i <= pagination.page + 2)) {
            html += `<li class="page-item ${i === pagination.page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="searchProgrammes(${i}); return false;">${i}</a>
            </li>`;
        } else if (i === pagination.page - 3 || i === pagination.page + 3) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }
    
    html += `<li class="page-item ${pagination.page === pagination.pages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="searchProgrammes(${pagination.page + 1}); return false;">Next</a>
    </li>`;
    
    html += '</ul></nav>';
    container.innerHTML = html;
}

