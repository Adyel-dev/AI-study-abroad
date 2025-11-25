// Immigration page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('immigrationForm');
    if (form) {
        form.addEventListener('submit', handleImmigrationForm);
    }
});

async function handleImmigrationForm(e) {
    e.preventDefault();
    
    const resultContainer = document.getElementById('adviceResult');
    if (resultContainer) {
        resultContainer.innerHTML = '<div class="spinner-border text-primary" role="status"></div>';
    }
    
    try {
        const data = {
            nationality: document.getElementById('nationality').value,
            planned_level: document.getElementById('plannedLevel').value,
            has_admission_letter: document.getElementById('hasAdmission').value === 'true',
            scholarship: document.getElementById('scholarship').value === 'true',
            language_of_instruction: document.getElementById('languageOfInstruction').value || undefined
        };
        
        const result = await apiPost('/immigration/advice', data);
        
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Immigration Advice</h5>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-warning">
                            <strong>Disclaimer:</strong> ${result.disclaimer}
                        </div>
                        <h6>Recommended Visa Types</h6>
                        <ul>
                            ${result.recommended_visa_types.map(type => `<li>${type}</li>`).join('')}
                        </ul>
                        <p>${result.summary}</p>
                        
                        ${result.funds_required ? `
                            <h6>Financial Requirements</h6>
                            <ul>
                                <li>Annual: €${result.funds_required.annual.toLocaleString()}</li>
                                <li>Monthly: €${result.funds_required.monthly.toLocaleString()}</li>
                                <li>Blocked Account: ${result.funds_required.blocked_account ? 'Yes' : 'No'}</li>
                            </ul>
                        ` : ''}
                        
                        ${result.work_allowed ? `
                            <h6>Work Permissions</h6>
                            <ul>
                                <li>Hours per week: ${result.work_allowed.hours_per_week}</li>
                                ${result.work_allowed.full_days_per_year ? 
                                    `<li>Full days per year: ${result.work_allowed.full_days_per_year}</li>` : ''}
                            </ul>
                        ` : ''}
                        
                        ${result.duration ? `
                            <h6>Duration</h6>
                            <ul>
                                <li>Initial: ${result.duration.initial_months} months</li>
                                <li>${result.duration.extension_rules}</li>
                            </ul>
                        ` : ''}
                        
                        ${result.key_documents && result.key_documents.length > 0 ? `
                            <h6>Key Documents Required</h6>
                            <ul>
                                ${result.key_documents.map(doc => `<li>${doc}</li>`).join('')}
                            </ul>
                        ` : ''}
                        
                        ${result.key_requirements && result.key_requirements.length > 0 ? `
                            <h6>Key Requirements</h6>
                            <ul>
                                ${result.key_requirements.map(req => `<li>${req}</li>`).join('')}
                            </ul>
                        ` : ''}
                        
                        ${result.source_urls && result.source_urls.length > 0 ? `
                            <h6>Source Links</h6>
                            <ul>
                                ${result.source_urls.map(url => `<li><a href="${url}" target="_blank">${url}</a></li>`).join('')}
                            </ul>
                        ` : ''}
                    </div>
                </div>
            `;
        }
    } catch (error) {
        showError('Failed to get immigration advice: ' + error.message);
        if (resultContainer) {
            resultContainer.innerHTML = '<div class="alert alert-danger">Error getting advice.</div>';
        }
    }
}
