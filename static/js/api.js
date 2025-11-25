/**
 * Centralized API wrapper for fetch calls
 */

const API_BASE = '/api';

/**
 * Make an API request
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise} Response data
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin'
    };
    
    const config = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * GET request
 */
async function apiGet(endpoint) {
    return apiRequest(endpoint, { method: 'GET' });
}

/**
 * POST request
 */
async function apiPost(endpoint, data) {
    return apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

/**
 * PUT request
 */
async function apiPut(endpoint, data) {
    return apiRequest(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

/**
 * DELETE request
 */
async function apiDelete(endpoint) {
    return apiRequest(endpoint, { method: 'DELETE' });
}

/**
 * POST form data (for file uploads)
 */
async function apiPostForm(endpoint, formData) {
    return apiRequest(endpoint, {
        method: 'POST',
        body: formData,
        headers: {} // Let browser set Content-Type for FormData
    });
}

/**
 * Show error message
 */
function showError(message, container = null) {
    const alert = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    if (container) {
        container.innerHTML = alert;
    } else {
        // Show at top of page
        const alertContainer = document.createElement('div');
        alertContainer.innerHTML = alert;
        document.body.insertBefore(alertContainer, document.body.firstChild);
        setTimeout(() => {
            alertContainer.remove();
        }, 5000);
    }
}

/**
 * Show success message
 */
function showSuccess(message, container = null) {
    const alert = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    if (container) {
        container.innerHTML = alert;
    } else {
        const alertContainer = document.createElement('div');
        alertContainer.innerHTML = alert;
        document.body.insertBefore(alertContainer, document.body.firstChild);
        setTimeout(() => {
            alertContainer.remove();
        }, 5000);
    }
}

/**
 * Show loading spinner
 */
function showLoading(element) {
    element.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

