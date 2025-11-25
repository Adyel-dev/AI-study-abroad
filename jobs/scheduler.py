"""
Background job scheduler using APScheduler
Schedules daily university sync and weekly programme scraping
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from scrapers.hipolabs_universities import sync_german_universities
from scrapers.daad_programmes import scrape_german_programmes

logger = logging.getLogger(__name__)

scheduler = None

def init_scheduler(app):
    """
    Initialize and start the scheduler
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return
    
    scheduler = BackgroundScheduler(daemon=True)
    
    # Schedule daily university sync at 2 AM UTC
    scheduler.add_job(
        sync_universities_job,
        trigger=CronTrigger(hour=2, minute=0),
        id='sync_universities',
        name='Sync German Universities from Hipolabs',
        replace_existing=True
    )
    
    # Schedule weekly programme scraping on Monday at 3 AM UTC
    scheduler.add_job(
        scrape_programmes_job,
        trigger=CronTrigger(day_of_week='mon', hour=3, minute=0),
        id='scrape_programmes',
        name='Scrape German Programmes',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background scheduler started")
    
    # Also register shutdown handler
    import atexit
    atexit.register(lambda: shutdown_scheduler())

def sync_universities_job():
    """Wrapper for university sync job"""
    try:
        logger.info("Starting scheduled university sync")
        sync_german_universities()
        logger.info("Scheduled university sync completed")
    except Exception as e:
        logger.error(f"Error in scheduled university sync: {e}")

def scrape_programmes_job():
    """Wrapper for programme scraping job"""
    try:
        logger.info("Starting scheduled programme scraping")
        scrape_german_programmes()
        logger.info("Scheduled programme scraping completed")
    except Exception as e:
        logger.error(f"Error in scheduled programme scraping: {e}")

def shutdown_scheduler():
    """Shutdown the scheduler"""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown()
        logger.info("Background scheduler shut down")

