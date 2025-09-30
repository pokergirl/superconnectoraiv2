import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from app.services.follow_up_email_service import process_pending_follow_ups, process_manual_follow_ups
from app.core.db import get_database
import traceback

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.check_interval = 3600  # Check every hour (3600 seconds)
    
    async def start(self):
        """Start the scheduler service"""
        if self.running:
            logger.warning("Scheduler service is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler service started")
    
    async def stop(self):
        """Stop the scheduler service"""
        if not self.running:
            logger.warning("Scheduler service is not running")
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Scheduler service stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop that runs background tasks"""
        logger.info(f"Scheduler loop started, checking every {self.check_interval} seconds")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running:
            try:
                start_time = datetime.utcnow()
                logger.debug(f"Starting scheduler cycle at {start_time}")
                
                # Process pending follow-up emails (legacy system)
                await self._process_follow_up_emails()
                
                # Manual follow-up emails are now handled via UI - no automated processing
                logger.info("Manual follow-up email system active - no automated processing needed")
                
                # Reset error counter on successful cycle
                consecutive_errors = 0
                
                end_time = datetime.utcnow()
                cycle_duration = (end_time - start_time).total_seconds()
                logger.debug(f"Scheduler cycle completed in {cycle_duration:.2f} seconds")
                
                # Wait for the next check interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error in scheduler loop (error #{consecutive_errors}): {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"Scheduler has failed {consecutive_errors} consecutive times. Stopping scheduler to prevent resource exhaustion.")
                    self.running = False
                    break
                
                # Exponential backoff for errors, but cap at 5 minutes
                error_wait_time = min(60 * (2 ** (consecutive_errors - 1)), 300)
                logger.info(f"Waiting {error_wait_time} seconds before retrying due to error")
                await asyncio.sleep(error_wait_time)
        
        logger.info("Scheduler loop ended")
    
    async def _process_follow_up_emails(self):
        """Process pending follow-up emails with enhanced error handling"""
        try:
            start_time = datetime.utcnow()
            processed_count = await process_pending_follow_ups()
            end_time = datetime.utcnow()
            
            duration = (end_time - start_time).total_seconds()
            
            if processed_count > 0:
                logger.info(f"Processed {processed_count} follow-up emails in {duration:.2f} seconds")
            else:
                logger.debug(f"No pending follow-up emails to process (checked in {duration:.2f} seconds)")
                
        except Exception as e:
            logger.error(f"Error processing follow-up emails: {str(e)}")
            logger.error(f"Follow-up email processing traceback: {traceback.format_exc()}")
            # Don't re-raise - let the scheduler continue with other tasks
    
    async def _process_automated_follow_ups(self):
        """Process automated follow-up emails for warm intro requests with enhanced error handling"""
        try:
            start_time = datetime.utcnow()
            processed_count = await process_automated_follow_ups()
            end_time = datetime.utcnow()
            
            duration = (end_time - start_time).total_seconds()
            
            if processed_count > 0:
                logger.info(f"Processed {processed_count} automated follow-up emails in {duration:.2f} seconds")
            else:
                logger.debug(f"No eligible warm intro requests for follow-up (checked in {duration:.2f} seconds)")
                
        except Exception as e:
            logger.error(f"Error processing automated follow-up emails: {str(e)}")
            logger.error(f"Automated follow-up processing traceback: {traceback.format_exc()}")
            # Don't re-raise - let the scheduler continue with other tasks
    
    def set_check_interval(self, seconds: int):
        """Set the check interval in seconds"""
        if seconds < 60:  # Minimum 1 minute
            raise ValueError("Check interval must be at least 60 seconds")
        
        self.check_interval = seconds
        logger.info(f"Check interval updated to {seconds} seconds")

# Global scheduler instance
scheduler_service = SchedulerService()

async def start_scheduler():
    """Start the global scheduler service"""
    await scheduler_service.start()

async def stop_scheduler():
    """Stop the global scheduler service"""
    await scheduler_service.stop()

async def get_scheduler_status():
    """Get the current status of the scheduler with enhanced information"""
    return {
        "running": scheduler_service.running,
        "check_interval": scheduler_service.check_interval,
        "next_check": datetime.utcnow() + timedelta(seconds=scheduler_service.check_interval) if scheduler_service.running else None,
        "current_time": datetime.utcnow().isoformat(),
        "task_active": scheduler_service.task is not None and not scheduler_service.task.done() if scheduler_service.task else False
    }

async def trigger_manual_follow_up_processing():
    """Manually trigger follow-up email processing (for admin use)"""
    try:
        logger.info("Manual follow-up processing triggered")
        
        # Process both types of follow-ups
        legacy_count = await process_pending_follow_ups()
        automated_count = await process_automated_follow_ups()
        
        total_processed = legacy_count + automated_count
        
        logger.info(f"Manual processing complete: {legacy_count} legacy + {automated_count} automated = {total_processed} total")
        
        return {
            "success": True,
            "legacy_processed": legacy_count,
            "automated_processed": automated_count,
            "total_processed": total_processed,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in manual follow-up processing: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }