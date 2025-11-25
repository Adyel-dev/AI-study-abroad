// Admin page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    checkAdminAuth();
    
    const loginForm = document.getElementById('adminLoginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleAdminLogin);
    }
});

async function checkAdminAuth() {
    // Check if already logged in (this would need session check)
    // For now, just show login form
}

async function handleAdminLogin(e) {
    e.preventDefault();
    
    try {
        const data = {
            username: document.getElementById('adminUsername').value,
            password: document.getElementById('adminPassword').value
        };
        
        const result = await apiPost('/admin/login', data);
        if (result.admin) {
            document.getElementById('loginSection').classList.add('d-none');
            document.getElementById('adminDashboard').classList.remove('d-none');
            loadDashboard();
        }
    } catch (error) {
        showError('Login failed: ' + error.message);
    }
}

async function adminLogout() {
    try {
        await apiPost('/admin/logout', {});
        document.getElementById('loginSection').classList.remove('d-none');
        document.getElementById('adminDashboard').classList.add('d-none');
    } catch (error) {
        console.error('Logout error:', error);
    }
}

async function loadDashboard() {
    loadStats();
    loadJobLogs();
    loadImmigrationRules();
}

async function loadStats() {
    const container = document.getElementById('statsContainer');
    if (!container) return;
    
    try {
        const data = await apiGet('/admin/stats');
        container.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card bg-primary text-white mb-3">
                        <div class="card-body">
                            <h6>Universities</h6>
                            <h3>${data.stats.universities}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white mb-3">
                        <div class="card-body">
                            <h6>Programmes</h6>
                            <h3>${data.stats.programmes}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white mb-3">
                        <div class="card-body">
                            <h6>Immigration Rules</h6>
                            <h3>${data.stats.immigration_rules}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white mb-3">
                        <div class="card-body">
                            <h6>Profiles</h6>
                            <h3>${data.stats.student_profiles}</h3>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (error) {
        container.innerHTML = '<div class="alert alert-danger">Error loading stats.</div>';
    }
}

async function triggerJob(jobType, collection = null) {
    try {
        const data = { job_type: jobType };
        if (collection) data.collection = collection;
        
        const result = await apiPost('/admin/jobs/trigger', data);
        showSuccess(`Job triggered: ${result.message}`);
        setTimeout(() => {
            loadJobLogs();
            loadStats();
        }, 2000);
    } catch (error) {
        showError('Failed to trigger job: ' + error.message);
    }
}

async function loadJobLogs() {
    const container = document.getElementById('jobLogsContainer');
    if (!container) return;
    
    try {
        const data = await apiGet('/admin/jobs?limit=10');
        if (data.jobs && data.jobs.length > 0) {
            container.innerHTML = `
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Job Type</th>
                                <th>Status</th>
                                <th>Created At</th>
                                <th>Result</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.jobs.map(job => `
                                <tr>
                                    <td>${job.job_type}</td>
                                    <td><span class="badge bg-${job.status === 'success' ? 'success' : job.status === 'error' ? 'danger' : 'warning'}">${job.status}</span></td>
                                    <td>${formatDate(job.created_at)}</td>
                                    <td>${job.result ? JSON.stringify(job.result).substring(0, 100) + '...' : ''}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            container.innerHTML = '<p class="text-muted">No job logs yet.</p>';
        }
    } catch (error) {
        container.innerHTML = '<div class="alert alert-danger">Error loading job logs.</div>';
    }
}

async function loadImmigrationRules() {
    const container = document.getElementById('immigrationRulesContainer');
    if (!container) return;
    
    try {
        const data = await apiGet('/admin/immigration-rules');
        if (data.rules && data.rules.length > 0) {
            container.innerHTML = `
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Country</th>
                                <th>Visa Type</th>
                                <th>Funds Required (EUR/year)</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.rules.map(rule => `
                                <tr>
                                    <td>${rule.country_code}</td>
                                    <td>${rule.visa_type}</td>
                                    <td>€${rule.min_funds_year_eur || 'N/A'}</td>
                                    <td>
                                        <button class="btn btn-sm btn-danger" onclick="deleteRule('${rule._id}')">Delete</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            container.innerHTML = '<p class="text-muted">No immigration rules found.</p>';
        }
    } catch (error) {
        container.innerHTML = '<div class="alert alert-danger">Error loading immigration rules.</div>';
    }
}

async function deleteRule(ruleId) {
    if (!confirm('Are you sure you want to delete this rule?')) return;
    
    try {
        await apiDelete(`/admin/immigration-rules/${ruleId}`);
        showSuccess('Rule deleted successfully!');
        loadImmigrationRules();
    } catch (error) {
        showError('Failed to delete rule: ' + error.message);
    }
}

function showAddRuleModal() {
    // Simple implementation - in production, use Bootstrap modal
    const ruleData = prompt('Enter rule JSON or use admin API to add rules');
    if (ruleData) {
        // Would need to parse and call API
        console.log('Add rule:', ruleData);
    }
}

