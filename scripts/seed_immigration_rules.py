"""
Seed script for initial immigration rules data
Run this script to populate initial immigration rules for Germany
"""
import sys
import os
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.mongo import get_db

logger = logging.getLogger(__name__)

def seed_immigration_rules():
    """Seed initial immigration rules for Germany"""
    db = get_db()
    
    # Clear existing rules (optional - comment out to keep existing)
    # db.immigration_rules.delete_many({'country_code': 'DE'})
    
    rules = [
        {
            'country_code': 'DE',
            'visa_type': 'National Study Visa (D-Study)',
            'min_funds_month_eur': 934,
            'min_funds_year_eur': 11208,
            'work_hours_per_week': 20,
            'max_full_days_per_year': 120,
            'duration_initial_months': 3,
            'extension_rules': 'Can be extended based on study duration. Apply before expiry at local Foreigners Office.',
            'key_documents': [
                'Valid passport',
                'Admission letter from German university',
                'Proof of financial means (blocked account with €11,208/year)',
                'Health insurance certificate',
                'Passport photos',
                'Completed visa application form',
                'Motivation letter',
                'Previous education certificates'
            ],
            'source_urls': [
                'https://www.make-it-in-germany.com/en/visa-residence/types/studying',
                'https://www.study-in-germany.com/en/plan-your-studies/requirements/visa/'
            ],
            'last_verified_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        },
        {
            'country_code': 'DE',
            'visa_type': 'Residence Permit for Study',
            'min_funds_month_eur': 934,
            'min_funds_year_eur': 11208,
            'work_hours_per_week': 20,
            'max_full_days_per_year': 120,
            'duration_initial_months': 12,
            'extension_rules': 'Can be extended annually based on study progress. Maximum duration depends on degree programme.',
            'key_documents': [
                'Valid passport',
                'University enrollment certificate',
                'Proof of financial means',
                'Health insurance certificate',
                'Registration certificate (Anmeldung)',
                'Passport photos',
                'Completed application form'
            ],
            'source_urls': [
                'https://www.make-it-in-germany.com/en/visa-residence/types/studying',
                'https://www.bamf.de/EN/Themen/MigrationAufenthalt/ZuwandererDrittstaaten/Studierende/studierende-node.html'
            ],
            'last_verified_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        },
        {
            'country_code': 'DE',
            'visa_type': 'Post-Study Job Search Residence Permit',
            'min_funds_month_eur': 934,
            'min_funds_year_eur': 11208,
            'work_hours_per_week': None,  # No limit during job search
            'max_full_days_per_year': None,
            'duration_initial_months': 18,
            'extension_rules': 'Cannot be extended beyond 18 months. Must find qualified employment within this period.',
            'key_documents': [
                'Valid passport',
                'University degree certificate',
                'Proof of financial means',
                'Health insurance certificate',
                'Proof of job search activities',
                'Passport photos',
                'Completed application form'
            ],
            'source_urls': [
                'https://www.make-it-in-germany.com/en/visa-residence/types/studying',
                'https://www.bamf.de/EN/Themen/MigrationAufenthalt/ZuwandererDrittstaaten/Akademiker/akademiker-node.html'
            ],
            'last_verified_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        },
        {
            'country_code': 'DE',
            'visa_type': 'Language Course / Studienkolleg',
            'min_funds_month_eur': 934,
            'min_funds_year_eur': 11208,
            'work_hours_per_week': 0,  # Usually not allowed during language courses
            'max_full_days_per_year': None,
            'duration_initial_months': 12,
            'extension_rules': 'Can be extended if continuing to Studienkolleg or university. Limited to preparation period.',
            'key_documents': [
                'Valid passport',
                'Admission letter from language school or Studienkolleg',
                'Proof of financial means',
                'Health insurance certificate',
                'Previous education certificates',
                'Passport photos',
                'Completed visa application form'
            ],
            'source_urls': [
                'https://www.study-in-germany.com/en/plan-your-studies/requirements/visa/',
                'https://www.hochschulkompass.de/en/degree-programmes/studienkolleg.html'
            ],
            'last_verified_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
    ]
    
    inserted = 0
    updated = 0
    
    for rule in rules:
        # Check if rule already exists
        existing = db.immigration_rules.find_one({
            'country_code': rule['country_code'],
            'visa_type': rule['visa_type']
        })
        
        if existing:
            # Update existing
            db.immigration_rules.update_one(
                {'_id': existing['_id']},
                {'$set': {k: v for k, v in rule.items() if k != 'created_at'}}
            )
            updated += 1
        else:
            # Insert new
            db.immigration_rules.insert_one(rule)
            inserted += 1
    
    print(f"Immigration rules seeding completed:")
    print(f"  - Inserted: {inserted}")
    print(f"  - Updated: {updated}")
    print(f"  - Total rules in database: {db.immigration_rules.count_documents({'country_code': 'DE'})}")

if __name__ == '__main__':
    try:
        seed_immigration_rules()
    except Exception as e:
        print(f"Error seeding immigration rules: {e}")
        sys.exit(1)

