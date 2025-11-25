// Profile page JavaScript

let currentProfile = null;

document.addEventListener('DOMContentLoaded', function() {
    loadProfile();
    loadDocuments();
    loadAssessment();
    
    // Profile form
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileSubmit);
    }
    
    // Document upload form
    const uploadForm = document.getElementById('documentUploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleDocumentUpload);
    }
});

async function loadProfile() {
    try {
        const data = await apiGet('/profile');
        if (data.profile) {
            currentProfile = data.profile;
            populateProfileForm(data.profile);
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

function populateProfileForm(profile) {
    if (!profile) return;
    
    document.getElementById('name').value = profile.name || '';
    document.getElementById('nationality').value = profile.nationality || '';
    document.getElementById('countryOfResidence').value = profile.country_of_residence || '';
    document.getElementById('highestEducation').value = profile.highest_education_level || '';
    document.getElementById('educationField').value = profile.highest_education_field || '';
    document.getElementById('gpa').value = profile.gpa_or_marks || '';
    document.getElementById('englishLevel').value = profile.english_level || '';
    document.getElementById('germanLevel').value = profile.german_level || '';
    document.getElementById('desiredLevel').value = profile.desired_study_level || '';
    document.getElementById('desiredField').value = profile.desired_field || '';
    document.getElementById('preferredCities').value = Array.isArray(profile.preferred_cities) ? 
        profile.preferred_cities.join(', ') : (profile.preferred_cities || '');
}

async function handleProfileSubmit(e) {
    e.preventDefault();
    
    try {
        const data = {
            name: document.getElementById('name').value,
            nationality: document.getElementById('nationality').value,
            country_of_residence: document.getElementById('countryOfResidence').value,
            highest_education_level: document.getElementById('highestEducation').value,
            highest_education_field: document.getElementById('educationField').value,
            gpa_or_marks: document.getElementById('gpa').value,
            english_level: document.getElementById('englishLevel').value,
            german_level: document.getElementById('germanLevel').value,
            desired_study_level: document.getElementById('desiredLevel').value,
            desired_field: document.getElementById('desiredField').value,
            preferred_cities: document.getElementById('preferredCities').value.split(',').map(c => c.trim()).filter(c => c)
        };
        
        const result = await apiPost('/profile', data);
        showSuccess('Profile saved successfully!');
        currentProfile = result.profile;
    } catch (error) {
        showError('Failed to save profile: ' + error.message);
    }
}

async function loadDocuments() {
    const container = document.getElementById('documentsList');
    if (!container) return;
    
    try {
        const data = await apiGet('/documents');
        if (data.documents && data.documents.length > 0) {
            container.innerHTML = `
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Filename</th>
                                <th>Uploaded</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.documents.map(doc => `
                                <tr>
                                    <td>${doc.document_type}</td>
                                    <td>${doc.original_filename}</td>
                                    <td>${formatDate(doc.uploaded_at)}</td>
                                    <td>
                                        <button class="btn btn-sm btn-danger" onclick="deleteDocument('${doc._id}')">
                                            <i class="bi bi-trash"></i> Delete
                                        </button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            container.innerHTML = '<p class="text-muted">No documents uploaded yet.</p>';
        }
    } catch (error) {
        container.innerHTML = '<div class="alert alert-danger">Error loading documents.</div>';
    }
}

async function handleDocumentUpload(e) {
    e.preventDefault();
    
    const formData = new FormData();
    const fileInput = document.getElementById('documentFile');
    const typeSelect = document.getElementById('documentType');
    
    if (!fileInput.files[0]) {
        showError('Please select a file');
        return;
    }
    
    formData.append('file', fileInput.files[0]);
    formData.append('document_type', typeSelect.value);
    
    try {
        await apiPostForm('/documents', formData);
        showSuccess('Document uploaded successfully!');
        fileInput.value = '';
        loadDocuments();
    } catch (error) {
        showError('Failed to upload document: ' + error.message);
    }
}

async function deleteDocument(docId) {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
        await apiDelete(`/documents/${docId}`);
        showSuccess('Document deleted successfully!');
        loadDocuments();
    } catch (error) {
        showError('Failed to delete document: ' + error.message);
    }
}

async function loadAssessment() {
    try {
        const data = await apiGet('/assessments/latest');
        if (data.assessment) {
            displayAssessment(data.assessment);
        }
    } catch (error) {
        console.error('Error loading assessment:', error);
    }
}

function displayAssessment(assessment) {
    const container = document.getElementById('assessmentResult');
    if (!container) return;
    
    const feasibilityClass = assessment.overall_feasibility.toLowerCase().replace(' ', '-');
    
    container.innerHTML = `
        <div class="assessment-result ${feasibilityClass}">
            <h5>Feasibility: ${assessment.overall_feasibility}</h5>
            <p><strong>Suggested Path:</strong> ${assessment.suggested_entry_path}</p>
            ${assessment.score_details ? `
                <p><strong>Score:</strong> ${assessment.score_details.percentage}%</p>
            ` : ''}
            ${assessment.key_gaps && assessment.key_gaps.length > 0 ? `
                <h6>Key Gaps:</h6>
                <ul>
                    ${assessment.key_gaps.map(gap => `<li>${gap}</li>`).join('')}
                </ul>
            ` : ''}
            ${assessment.recommended_actions && assessment.recommended_actions.length > 0 ? `
                <h6>Recommended Actions:</h6>
                <ul>
                    ${assessment.recommended_actions.map(action => `<li>${action}</li>`).join('')}
                </ul>
            ` : ''}
            ${assessment.ai_explanation ? `
                <p>${assessment.ai_explanation}</p>
            ` : ''}
            <div class="alert alert-info mt-3">
                <small>${assessment.disclaimer || 'This assessment is informational only.'}</small>
            </div>
        </div>
    `;
}

async function runAssessment() {
    const container = document.getElementById('assessmentResult');
    if (container) {
        container.innerHTML = '<div class="spinner-border text-primary" role="status"></div>';
    }
    
    try {
        const result = await apiPost('/assessments/run', {});
        displayAssessment(result.assessment);
        showSuccess('Assessment completed!');
    } catch (error) {
        showError('Failed to run assessment: ' + error.message);
        if (container) {
            container.innerHTML = '<div class="alert alert-danger">Error running assessment.</div>';
        }
    }
}

