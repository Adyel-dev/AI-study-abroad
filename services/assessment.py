"""
Assessment service
Implements rule-based feasibility assessment for studying in Germany
"""
import logging
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

ASSESSMENT_DISCLAIMER = "This assessment is informational only and not an admission, scholarship, or visa decision."

def run_assessment(profile, documents, immigration_rules_de=None):
    """
    Run feasibility assessment based on profile and documents
    
    Args:
        profile: Student profile dictionary
        documents: List of document dictionaries
        immigration_rules_de: Immigration rules for Germany (optional)
    
    Returns:
        Assessment dictionary with feasibility score and recommendations
    """
    try:
        # Initialize assessment
        assessment = {
            'country_target': 'DE',
            'overall_feasibility': 'Needs Preparation',
            'suggested_entry_path': None,
            'key_gaps': [],
            'recommended_actions': [],
            'ai_explanation': '',
            'score_details': {}
        }
        
        # Calculate feasibility score (0-100)
        score = 0
        max_score = 0
        
        # 1. Education level check (30 points)
        max_score += 30
        education_level = profile.get('highest_education_level', '').lower()
        desired_level = profile.get('desired_study_level', '').lower()
        
        if desired_level == 'bachelor':
            if education_level in ['high school', 'secondary']:
                score += 30
            elif education_level in ['bachelor']:
                score += 15  # Already has bachelor
            else:
                assessment['key_gaps'].append('High school diploma required for Bachelor programmes')
        elif desired_level == 'master':
            if education_level in ['bachelor', 'undergraduate']:
                score += 30
            elif education_level in ['master']:
                score += 15  # Already has master
            else:
                assessment['key_gaps'].append('Bachelor degree required for Master programmes')
        elif desired_level in ['phd', 'doctorate']:
            if education_level in ['master', 'graduate']:
                score += 30
            else:
                assessment['key_gaps'].append('Master degree typically required for PhD programmes')
        elif desired_level == 'studienkolleg':
            if education_level in ['high school', 'secondary']:
                score += 30
            else:
                assessment['key_gaps'].append('High school diploma required for Studienkolleg')
        
        # 2. Language requirements (25 points)
        max_score += 25
        language_score = 0
        
        desired_field = profile.get('desired_field', '').lower()
        english_level = profile.get('english_level', '').lower() or ''
        german_level = profile.get('german_level', '').lower() or ''
        
        # Check for language certificates in documents
        has_language_cert = any(
            doc.get('document_type') == 'language_certificate' 
            for doc in documents
        )
        
        if has_language_cert:
            language_score += 10
        
        # English programmes
        if 'english' in desired_field or any(keyword in english_level for keyword in ['ielts', 'toefl', 'cefr']):
            if 'ielts' in english_level or 'toefl' in english_level:
                language_score += 15
            elif has_language_cert:
                language_score += 10
            else:
                assessment['key_gaps'].append('English language certificate needed (IELTS/TOEFL)')
        
        # German programmes
        if 'german' in desired_field or german_level:
            if any(keyword in german_level for keyword in ['a1', 'a2', 'b1', 'b2', 'c1', 'c2', 'testdaf', 'dsh']):
                if 'c1' in german_level or 'c2' in german_level or 'testdaf' in german_level:
                    language_score += 15
                elif 'b2' in german_level:
                    language_score += 12
                else:
                    language_score += 8
                    assessment['key_gaps'].append('Higher German proficiency may be required (typically C1)')
            else:
                assessment['key_gaps'].append('German language proficiency needed (typically C1 level or TestDaF)')
        
        score += language_score
        
        # 3. Academic documents (20 points)
        max_score += 20
        doc_score = 0
        
        has_transcript = any(doc.get('document_type') == 'transcript' for doc in documents)
        has_degree = any(doc.get('document_type') == 'degree_certificate' for doc in documents)
        
        if has_transcript:
            doc_score += 10
        else:
            assessment['key_gaps'].append('Academic transcripts needed')
        
        if has_degree:
            doc_score += 10
        else:
            if desired_level != 'bachelor':
                assessment['key_gaps'].append('Degree certificate needed')
        
        score += doc_score
        
        # 4. Profile completeness (15 points)
        max_score += 15
        profile_score = 0
        
        if profile.get('gpa_or_marks'):
            profile_score += 5
        else:
            assessment['recommended_actions'].append('Add GPA/marks to profile')
        
        if profile.get('desired_field'):
            profile_score += 5
        else:
            assessment['recommended_actions'].append('Specify desired field of study')
        
        if profile.get('preferred_cities'):
            profile_score += 5
        
        score += profile_score
        
        # 5. Additional documents (10 points)
        max_score += 10
        additional_doc_score = 0
        
        has_cv = any(doc.get('document_type') == 'CV' for doc in documents)
        has_sop = any(doc.get('document_type') == 'SOP' for doc in documents)
        
        if has_cv:
            additional_doc_score += 5
        else:
            assessment['recommended_actions'].append('Prepare a CV/Resume')
        
        if has_sop:
            additional_doc_score += 5
        else:
            assessment['recommended_actions'].append('Prepare a Statement of Purpose (SOP)')
        
        score += additional_doc_score
        
        # Calculate overall feasibility
        percentage = (score / max_score * 100) if max_score > 0 else 0
        
        if percentage >= 80:
            assessment['overall_feasibility'] = 'High'
        elif percentage >= 60:
            assessment['overall_feasibility'] = 'Medium'
        else:
            assessment['overall_feasibility'] = 'Needs Preparation'
        
        # Determine suggested entry path
        if desired_level == 'bachelor':
            if education_level not in ['high school', 'secondary']:
                assessment['suggested_entry_path'] = 'Consider Studienkolleg preparation course first'
            else:
                assessment['suggested_entry_path'] = 'Direct Bachelor application'
        elif desired_level == 'master':
            if education_level not in ['bachelor', 'undergraduate']:
                assessment['suggested_entry_path'] = 'Complete Bachelor degree first'
            else:
                assessment['suggested_entry_path'] = 'Direct Master application'
        elif desired_level == 'studienkolleg':
            assessment['suggested_entry_path'] = 'Apply for Studienkolleg (preparatory course)'
        elif desired_level in ['phd', 'doctorate']:
            assessment['suggested_entry_path'] = 'Find supervisor and apply for PhD position'
        else:
            assessment['suggested_entry_path'] = 'Language course then degree programme'
        
        # Add default recommended actions if none exist
        if not assessment['recommended_actions']:
            assessment['recommended_actions'].append('Continue preparing application documents')
            assessment['recommended_actions'].append('Research universities and programmes')
            assessment['recommended_actions'].append('Check application deadlines')
        
        # Generate AI explanation (optional, can use OpenAI)
        assessment['ai_explanation'] = generate_explanation(assessment, profile, percentage)
        
        # Store score details
        assessment['score_details'] = {
            'total_score': score,
            'max_score': max_score,
            'percentage': round(percentage, 1),
            'breakdown': {
                'education': score - language_score - doc_score - profile_score - additional_doc_score,
                'language': language_score,
                'documents': doc_score,
                'profile': profile_score,
                'additional_docs': additional_doc_score
            }
        }
        
        return assessment
        
    except Exception as e:
        logger.error(f"Error running assessment: {e}")
        raise

def generate_explanation(assessment, profile, percentage):
    """
    Generate human-readable explanation of assessment results
    Can be enhanced with OpenAI API call for more detailed explanations
    """
    explanation_parts = [
        f"Your feasibility score is {percentage:.0f}% ({assessment['overall_feasibility']} feasibility)."
    ]
    
    explanation_parts.append(f"Suggested path: {assessment['suggested_entry_path']}.")
    
    if assessment['key_gaps']:
        explanation_parts.append("Key areas that need attention:")
        for gap in assessment['key_gaps']:
            explanation_parts.append(f"- {gap}")
    
    if assessment['recommended_actions']:
        explanation_parts.append("Recommended next steps:")
        for action in assessment['recommended_actions'][:5]:  # Limit to 5
            explanation_parts.append(f"- {action}")
    
    return "\n".join(explanation_parts)

