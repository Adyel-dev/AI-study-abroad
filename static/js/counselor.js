// Counselor page JavaScript

let currentSessionId = null;

document.addEventListener('DOMContentLoaded', function() {
    loadSessions();
    loadProfileSummary();
    loadAssessmentSummary();
    loadActionPlan();
});

async function loadSessions() {
    try {
        const data = await apiGet('/counselor/sessions');
        const select = document.getElementById('sessionSelect');
        if (select && data.sessions) {
            select.innerHTML = '<option value="">Select Session...</option>' +
                data.sessions.map(session => 
                    `<option value="${session._id}">${session.title} (${formatDate(session.created_at)})</option>`
                ).join('');
            
            if (data.sessions.length > 0 && !currentSessionId) {
                currentSessionId = data.sessions[0]._id;
                select.value = currentSessionId;
                loadSession();
            }
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

async function createNewSession() {
    try {
        const result = await apiPost('/counselor/sessions', {
            title: 'New Session',
            purpose: 'general'
        });
        currentSessionId = result.session._id;
        loadSessions();
        loadSession();
    } catch (error) {
        showError('Failed to create session: ' + error.message);
    }
}

async function loadSession() {
    const sessionId = document.getElementById('sessionSelect')?.value;
    if (!sessionId) {
        currentSessionId = null;
        document.getElementById('chatContainer').innerHTML = '<p class="text-muted text-center">Select or create a session to start chatting.</p>';
        return;
    }
    
    currentSessionId = sessionId;
    
    try {
        const data = await apiGet(`/counselor/sessions/${sessionId}/messages`);
        displayMessages(data.messages || []);
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

function displayMessages(messages) {
    const container = document.getElementById('chatContainer');
    if (!container) return;
    
    if (messages.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No messages yet. Start the conversation!</p>';
        return;
    }
    
    container.innerHTML = messages.map(msg => `
        <div class="chat-message ${msg.sender}">
            <strong>${msg.sender === 'user' ? 'You' : 'AI Counselor'}:</strong>
            <p>${msg.message_text}</p>
            ${msg.sources && msg.sources.length > 0 ? `
                <small><strong>Sources:</strong> ${msg.sources.map(s => 
                    s.url ? `<a href="${s.url}" target="_blank">${s.title}</a>` : s.title
                ).join(', ')}</small>
            ` : ''}
        </div>
    `).join('');
    
    container.scrollTop = container.scrollHeight;
}

async function sendMessage(e) {
    e.preventDefault();
    
    if (!currentSessionId) {
        showError('Please select or create a session first.');
        return;
    }
    
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;
    
    // Display user message immediately
    const container = document.getElementById('chatContainer');
    container.innerHTML += `
        <div class="chat-message user">
            <strong>You:</strong>
            <p>${message}</p>
        </div>
    `;
    container.scrollTop = container.scrollHeight;
    
    input.value = '';
    
    // Show loading indicator
    container.innerHTML += `
        <div class="chat-message assistant">
            <div class="spinner-border spinner-border-sm" role="status"></div> Thinking...
        </div>
    `;
    container.scrollTop = container.scrollHeight;
    
    try {
        const result = await apiPost(`/counselor/sessions/${currentSessionId}/message`, {
            message: message
        });
        
        // Remove loading indicator and add response
        container.innerHTML = container.innerHTML.replace(
            /<div class="chat-message assistant">[\s\S]*?Thinking\.\.\.<\/div>$/,
            ''
        );
        
        container.innerHTML += `
            <div class="chat-message assistant">
                <strong>AI Counselor:</strong>
                <p>${result.assistant_message.text}</p>
                ${result.assistant_message.sources && result.assistant_message.sources.length > 0 ? `
                    <small><strong>Sources:</strong> ${result.assistant_message.sources.map(s => 
                        s.url ? `<a href="${s.url}" target="_blank">${s.title}</a>` : s.title
                    ).join(', ')}</small>
                ` : ''}
            </div>
        `;
        
        container.scrollTop = container.scrollHeight;
        
        // Reload action plan if updated
        if (result.assistant_message.plan_updates) {
            loadActionPlan();
        }
    } catch (error) {
        showError('Failed to send message: ' + error.message);
        container.innerHTML = container.innerHTML.replace(
            /<div class="chat-message assistant">[\s\S]*?Thinking\.\.\.<\/div>$/,
            '<div class="chat-message assistant"><p class="text-danger">Error: Failed to get response.</p></div>'
        );
    }
}

async function loadProfileSummary() {
    const container = document.getElementById('profileSummary');
    if (!container) return;
    
    try {
        const data = await apiGet('/profile');
        if (data.profile) {
            container.innerHTML = `
                <p><strong>Nationality:</strong> ${data.profile.nationality || 'Not set'}</p>
                <p><strong>Education:</strong> ${data.profile.highest_education_level || 'Not set'}</p>
                <p><strong>Desired Level:</strong> ${data.profile.desired_study_level || 'Not set'}</p>
            `;
        }
    } catch (error) {
        console.error('Error loading profile summary:', error);
    }
}

async function loadAssessmentSummary() {
    const container = document.getElementById('assessmentSummary');
    if (!container) return;
    
    try {
        const data = await apiGet('/assessments/latest');
        if (data.assessment) {
            container.innerHTML = `
                <p><strong>Feasibility:</strong> <span class="badge bg-${data.assessment.overall_feasibility === 'High' ? 'success' : data.assessment.overall_feasibility === 'Medium' ? 'warning' : 'danger'}">${data.assessment.overall_feasibility}</span></p>
                <p><small>${data.assessment.suggested_entry_path || 'No path suggested'}</small></p>
            `;
        }
    } catch (error) {
        console.error('Error loading assessment summary:', error);
    }
}

async function loadActionPlan() {
    const container = document.getElementById('actionPlan');
    if (!container) return;
    
    try {
        const data = await apiGet('/counselor/plan');
        if (data.plan && data.plan.plan_steps) {
            if (data.plan.plan_steps.length === 0) {
                container.innerHTML = '<p class="text-muted small">No steps in action plan yet.</p>';
                return;
            }
            
            container.innerHTML = data.plan.plan_steps.map((step, idx) => `
                <div class="plan-step ${step.status}">
                    <strong>${idx + 1}. ${step.title}</strong>
                    <span class="badge bg-${step.status === 'completed' ? 'success' : step.status === 'in_progress' ? 'warning' : 'secondary'} float-end">${step.status}</span>
                    ${step.due_date ? `<br><small>Due: ${step.due_date}</small>` : ''}
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p class="text-muted small">No action plan available. Start a conversation to generate one!</p>';
        }
    } catch (error) {
        console.error('Error loading action plan:', error);
    }
}

