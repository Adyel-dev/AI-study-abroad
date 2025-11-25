"""
Counselor service - Enhanced human-like AI counselor
Proactive, question-driven counseling with intelligent database querying
"""
import logging
from typing import Dict, List, Any, Optional
from models.mongo import get_db
from services.embeddings import search_similar
from services.counselor_query import extract_search_intent, query_programmes_intelligent, query_universities_intelligent
from services.ai_client import chat_completion
from config import Config
from datetime import datetime
import re
import json

logger = logging.getLogger(__name__)

def get_conversation_state(session_id: str, history: List[Dict] = None) -> Dict:
    """
    Track conversation state - what information has been asked and gathered
    """
    state = {
        'questions_asked': [],
        'info_gathered': {},
        'last_question_type': None
    }
    
    if not history:
        return state
    
    # Analyze conversation history to track questions asked
    for msg in history:
        sender = msg.get('sender', '')
        text = msg.get('message_text', '').lower()
        
        if sender == 'assistant':
            # Detect if assistant asked a question
            question_keywords = {
                'nationality': ['nationality', 'country', 'where are you from'],
                'current_degree': ['current degree', 'education level', 'what degree', 'bachelor', 'master'],
                'desired_field': ['field of study', 'what subject', 'study', 'major'],
                'desired_level': ['degree level', 'master', 'bachelor', 'phd', 'studienkolleg'],
                'ielts_score': ['ielts', 'toefl', 'english', 'language test', 'english score'],
                'german_level': ['german', 'testdaf', 'german proficiency'],
                'budget': ['budget', 'funds', 'money', 'tuition', 'finance', 'cost'],
                'preferred_cities': ['city', 'cities', 'location', 'where', 'berlin', 'munich', 'hamburg']
            }
            
            for info_type, keywords in question_keywords.items():
                if any(keyword in text for keyword in keywords):
                    if '?' in msg.get('message_text', ''):
                        state['questions_asked'].append(info_type)
                        state['last_question_type'] = info_type
        
        elif sender == 'user':
            # Track information provided
            if 'nationality' in text or 'from' in text:
                state['info_gathered']['nationality'] = True
            if any(word in text for word in ['bachelor', 'master', 'phd', 'degree', 'graduated']):
                state['info_gathered']['current_degree'] = True
            if any(word in text for word in ['study', 'major', 'field', 'subject']):
                state['info_gathered']['desired_field'] = True
            if any(word in text for word in ['ielts', 'toefl', 'english']):
                state['info_gathered']['ielts_score'] = True
            if 'german' in text:
                state['info_gathered']['german_level'] = True
            if any(word in text for word in ['budget', 'funds', 'money', 'euro', 'eur']):
                state['info_gathered']['budget'] = True
    
    return state

def get_missing_profile_info(user_profile: Dict) -> List[str]:
    """
    Determine what profile information is missing
    Returns list of missing field names
    """
    missing = []
    
    if not user_profile:
        return ['nationality', 'highest_education_level', 'desired_study_level', 'desired_field']
    
    if not user_profile.get('nationality'):
        missing.append('nationality')
    if not user_profile.get('highest_education_level'):
        missing.append('current_degree')
    if not user_profile.get('desired_study_level'):
        missing.append('desired_degree_level')
    if not user_profile.get('desired_field'):
        missing.append('desired_field')
    if not user_profile.get('english_level'):
        missing.append('ielts_score')
    if not user_profile.get('german_level'):
        missing.append('german_level')
    
    return missing

def get_next_question(missing_info: List[str], conversation_state: Dict) -> Optional[str]:
    """
    Determine what question to ask next based on priority order
    Priority: current_degree -> desired_field -> desired_degree_level -> ielts_score -> german_level -> budget -> preferred_cities
    """
    priority_order = [
        'current_degree',
        'desired_field', 
        'desired_degree_level',
        'ielts_score',
        'german_level',
        'budget',
        'preferred_cities'
    ]
    
    # Check what hasn't been asked recently
    recently_asked = conversation_state.get('questions_asked', [])[-3:]  # Last 3 questions
    
    for field in priority_order:
        if field in missing_info and field not in recently_asked:
            return field
    
    # If all priority questions asked, return first missing
    if missing_info:
        return missing_info[0]
    
    return None

def extract_profile_updates(user_message: str, history: List[Dict] = None) -> Dict:
    """
    Extract profile information from user message using AI (OpenRouter/OpenAI)
    """
    try:
        
        history_text = ""
        if history:
            history_text = "\nRecent conversation:\n"
            for msg in history[-3:]:
                history_text += f"{msg.get('sender')}: {msg.get('message_text', '')}\n"
        
        prompt = f"""Extract student profile information from this message. Return ONLY a JSON object with these fields (null if not mentioned):
- nationality: country name
- highest_education_level: "High School", "Bachelor", "Master", "PhD"
- highest_education_field: field of study
- desired_study_level: "Bachelor", "Master", "PhD", "Studienkolleg", "Language course"
- desired_field: field of study they want
- english_level: IELTS/TOEFL score or CEFR level (e.g., "IELTS 7.0" or "C1")
- german_level: German proficiency (e.g., "B2" or "TestDaF")
- gpa_or_marks: GPA or percentage
- preferred_cities: array of city names
- budget_funds: approximate funds available in EUR per year

Message: {user_message}
{history_text}

Return JSON only:"""

        ai_response = chat_completion(
            messages=[
                {"role": "system", "content": "Extract structured data from messages. Return valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        content = ai_response['content'].strip()
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        content = content.strip()
        
        updates = json.loads(content)
        # Filter out null values
        return {k: v for k, v in updates.items() if v is not None}
        
    except Exception as e:
        logger.error(f"Error extracting profile updates: {e}")
        return {}

def generate_counselor_response(session_id: str, user_message: str, user_profile: Dict = None, 
                                assessment: Dict = None, plan: Dict = None, 
                                history: List[Dict] = None) -> Dict[str, Any]:
    """
    Generate counselor response with enhanced proactive, question-driven approach
    """
    try:
        db = get_db()
        
        # Extract profile updates from conversation
        profile_updates = extract_profile_updates(user_message, history)
        
        # Detect if user is asking about programmes/universities
        programme_keywords = ['university', 'programme', 'program', 'course', 'degree', 'study', 'master', 'bachelor', 'phd', 'it', 'engineering', 'business']
        is_programme_query = any(keyword in user_message.lower() for keyword in programme_keywords)
        
        # Build comprehensive context
        context_parts = []
        
        # 1. User profile context (with any updates)
        if user_profile:
            profile_data = {**user_profile, **profile_updates}
        else:
            profile_data = profile_updates or {}
            
        if profile_data:
            profile_context = f"""Student Profile:
- Nationality: {profile_data.get('nationality', 'Not specified')}
- Current Education: {profile_data.get('highest_education_level', 'Not specified')} in {profile_data.get('highest_education_field', 'Not specified')}
- GPA/Marks: {profile_data.get('gpa_or_marks', 'Not specified')}
- Desired Study Level: {profile_data.get('desired_study_level', 'Not specified')}
- Desired Field: {profile_data.get('desired_field', 'Not specified')}
- Preferred Cities: {', '.join(profile_data.get('preferred_cities', [])) if isinstance(profile_data.get('preferred_cities'), list) else (str(profile_data.get('preferred_cities', 'Not specified')) or 'Not specified')}
- English Level: {profile_data.get('english_level', 'Not specified')}
- German Level: {profile_data.get('german_level', 'Not specified') or 'Not specified'}
- Budget/Funds: {profile_data.get('budget_funds', 'Not specified')}
"""
            context_parts.append(profile_context)
        
        # 2. Intelligent database querying for programmes/universities
        programme_results = []
        university_results = []
        sources = []
        
        if is_programme_query:
            # Extract search intent from user message
            search_intent = extract_search_intent(user_message, history)
            
            # Query programmes database intelligently
            programme_results = query_programmes_intelligent(search_intent, profile_data, limit=10)
            
            # Also search universities if relevant
            university_results = query_universities_intelligent(search_intent, profile_data, limit=5)
            
            # Format programme results for context
            if programme_results:
                programme_context = "\n=== Available Programmes in Database ===\n"
                for prog in programme_results[:8]:  # Top 8 programmes
                    programme_context += f"""
Programme: {prog.get('title', 'Unknown')}
- University: {prog.get('university_name', 'Unknown')}
- Degree: {prog.get('degree_type', 'Not specified')}
- City: {prog.get('city', 'Not specified')}
- Language: {', '.join(prog.get('language', [])) if isinstance(prog.get('language'), list) else (prog.get('language', 'Not specified') or 'Not specified')}
- Tuition: {'€' + str(prog.get('tuition_fee_eur_per_semester')) + '/semester' if prog.get('tuition_fee_eur_per_semester') else 'Free/Not specified'}
- Duration: {str(prog.get('duration_semesters')) + ' semesters' if prog.get('duration_semesters') else 'Not specified'}
- Application Deadline: {prog.get('application_deadline', 'Not specified')}
- Source URL: {prog.get('source_url', 'Not available')}
---
"""
                    if prog.get('source_url'):
                        sources.append({
                            'title': f"{prog.get('title')} - {prog.get('university_name')}",
                            'url': prog.get('source_url')
                        })
                context_parts.append(programme_context)
            
            # Format university results
            if university_results and not programme_results:
                uni_context = "\n=== Available Universities in Database ===\n"
                for uni in university_results[:5]:
                    uni_context += f"""
University: {uni.get('name', 'Unknown')}
- State: {uni.get('state-province', 'Not specified')}
- Website: {uni.get('web_pages', [None])[0] or 'Not available'}
---
"""
                    if uni.get('web_pages'):
                        sources.append({
                            'title': uni.get('name'),
                            'url': uni.get('web_pages')[0]
                        })
                context_parts.append(uni_context)
        
        # 3. Assessment context
        if assessment:
            assessment_context = f"""Current Assessment:
- Feasibility: {assessment.get('overall_feasibility', 'Not assessed')}
- Suggested Path: {assessment.get('suggested_entry_path', 'Not specified')}
- Key Gaps: {', '.join(assessment.get('key_gaps', [])) or 'None identified'}
"""
            context_parts.append(assessment_context)
        
        # 4. Action plan context
        if plan and plan.get('plan_steps'):
            plan_context = "Current Action Plan:\n"
            for step in plan['plan_steps'][:5]:
                status = step.get('status', 'pending')
                plan_context += f"- {step.get('title', 'Step')} ({status})\n"
            context_parts.append(plan_context)
        
        # 5. Conversation history
        if history:
            history_context = "\nRecent Conversation:\n"
            for msg in history[-6:]:  # Last 6 messages
                sender = msg.get('sender', 'user')
                text = msg.get('message_text', '')[:150]
                history_context += f"{sender.capitalize()}: {text}\n"
            context_parts.append(history_context)
        
        # Get conversation state (what questions have been asked, what info gathered)
        conversation_state = get_conversation_state(session_id, history)
        
        # Determine missing profile information
        missing_info = get_missing_profile_info(profile_data)
        
        # Determine next question to ask
        next_question_field = get_next_question(missing_info, conversation_state)
        
        # Build enhanced system prompt
        system_prompt = """You are a friendly, proactive AI counselor helping international students study in Germany. Your role is to:

1. **Ask Questions Proactively**: When information is missing, ask targeted questions in a natural, conversational way. Don't just answer - help gather what you need to give the best recommendations.

2. **Provide Specific Recommendations**: When students ask about programmes or universities, search the database and provide SPECIFIC details from the available programmes list:
   - University name
   - Programme title  
   - Tuition fees (if available)
   - Language requirements
   - Duration
   - Application deadlines (if available)
   - City location
   
   NEVER say "visit the website" - provide the actual information from the database!

3. **Information Gathering Order**: When profile is incomplete, ask questions in this order:
   - Current degree/education level
   - Desired field of study
   - Desired degree level (Bachelor/Master/PhD)
   - IELTS/English proficiency score
   - German proficiency (if relevant)
   - Budget/financial situation (funds available per year)
   - Preferred cities in Germany

4. **Be Conversational**: Speak like a helpful human counselor, not a robot. Use natural language, be warm and encouraging.

5. **Immigration Disclaimer**: For visa/immigration questions, always include: "This is informational only and not legal advice. Always confirm with official embassies/authorities."

6. **Database First**: Always check the database for programmes/universities before giving generic advice. Use the specific programme details provided in the context.

IMPORTANT: If programmes are provided in the context, list them with specific details (fees, requirements, deadlines). Don't just mention names - give actionable information!"""

        # Add conversation state and next question to prompt
        if missing_info:
            state_context = f"\n\nConversation State:\n"
            state_context += f"- Missing information: {', '.join(missing_info)}\n"
            if next_question_field:
                state_context += f"- Next priority question: {next_question_field}\n"
            state_context += f"- Recently asked questions: {', '.join(conversation_state.get('questions_asked', [])[-3:]) or 'None'}\n"
            
            system_prompt += state_context
            system_prompt += "\nIMPORTANT: Ask for missing information in a natural, conversational way. Don't ask multiple questions at once - ask one at a time."
        
        # Build full context
        full_context = "\n".join(context_parts) if context_parts else "No additional context available."
        
        # Prepare messages with conversation history
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history to messages for better context
        if history and len(history) > 2:
            for msg in history[-4:-1]:  # Exclude last message (current one)
                role = "user" if msg.get('sender') == 'user' else "assistant"
                messages.append({
                    "role": role,
                    "content": msg.get('message_text', '')[:300]
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": f"Context:\n{full_context}\n\nStudent's question: {user_message}"
        })
        
        # Call AI API (OpenRouter primary, OpenAI fallback)
        try:
            ai_response = chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            answer = ai_response['content']
            logger.debug(f"AI response from {ai_response['provider']} using {ai_response['model']}")
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            answer = "I apologize, but I'm having trouble processing your request right now. Please try again later."
            raise
        
        # Extract plan updates
        plan_updates = None
        if any(keyword in user_message.lower() for keyword in ['goal', 'want to', 'plan to', 'need to', 'should']):
            plan_updates = extract_plan_updates(user_message, answer)
        
        return {
            'response': answer,
            'sources': sources,
            'plan_updates': plan_updates,
            'profile_updates': profile_updates  # Return extracted profile updates
        }
        
    except Exception as e:
        logger.error(f"Error generating counselor response: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

def extract_plan_updates(user_message: str, assistant_response: str) -> Dict:
    """Extract potential action plan updates from conversation"""
    updates = {
        'new_steps': [],
        'updated_steps': []
    }
    
    if 'apply' in user_message.lower():
        updates['new_steps'].append({
            'title': 'Prepare and submit applications',
            'status': 'pending',
            'notes': 'Based on conversation'
        })
    
    return updates
