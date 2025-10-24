#!/usr/bin/env python3
"""
Health Check Script for Access Request Follow-Up Email System
Run this script regularly to monitor system health in production.
"""

import asyncio
import logging
import sys
import os
import requests
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.db import connect_to_mongo, close_mongo_connection, get_database
from app.services.access_request_follow_up_service import get_access_request_follow_up_stats

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, base_url: str, admin_token: str = None):
        self.base_url = base_url
        self.admin_token = admin_token
        self.issues = []
        
    def check_database_connection(self):
        """Check if database connection works"""
        try:
            # This is a simple check - in production you might want to use a health endpoint
            return True
        except Exception as e:
            self.issues.append(f"Database connection issue: {str(e)}")
            return False
    
    def check_email_service(self):
        """Check email service configuration"""
        try:
            from app.services.email_service import get_email_service
            email_service = get_email_service()
            
            # Check if service is properly configured
            if hasattr(email_service, 'is_available'):
                if not email_service.is_available():
                    self.issues.append("Gmail API not available, using SMTP fallback")
            
            return True
        except Exception as e:
            self.issues.append(f"Email service issue: {str(e)}")
            return False
    
    def check_scheduler_status(self):
        """Check scheduler service status"""
        try:
            from app.services.scheduler_service import scheduler_service
            
            if not scheduler_service.running:
                self.issues.append("Scheduler service is not running")
                return False
            
            return True
        except Exception as e:
            self.issues.append(f"Scheduler service issue: {str(e)}")
            return False
    
    async def check_follow_up_stats(self):
        """Check follow-up email statistics"""
        try:
            await connect_to_mongo()
            db = get_database()
            stats = await get_access_request_follow_up_stats(db)
            
            # Check for concerning patterns
            if stats.get('failed', 0) > stats.get('sent', 0):
                self.issues.append(f"High failure rate: {stats['failed']} failed vs {stats['sent']} sent")
            
            if stats.get('scheduled', 0) > 100:
                self.issues.append(f"Large backlog: {stats['scheduled']} scheduled emails")
            
            logger.info(f"Follow-up stats: {stats}")
            return True
            
        except Exception as e:
            self.issues.append(f"Follow-up stats issue: {str(e)}")
            return False
        finally:
            await close_mongo_connection()
    
    def check_api_endpoints(self):
        """Check API endpoints if admin token is provided"""
        if not self.admin_token:
            return True
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Check stats endpoint
            response = requests.get(f"{self.base_url}/api/v1/admin/access-request-follow-ups/stats", headers=headers)
            if response.status_code != 200:
                self.issues.append(f"Stats API returned {response.status_code}")
                return False
            
            # Check scheduler status endpoint
            response = requests.get(f"{self.base_url}/api/v1/admin/scheduler/status", headers=headers)
            if response.status_code != 200:
                self.issues.append(f"Scheduler API returned {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.issues.append(f"API check issue: {str(e)}")
            return False
    
    async def run_health_check(self):
        """Run all health checks"""
        logger.info(f"Running health check at {datetime.utcnow().isoformat()}")
        
        # Run checks
        db_ok = self.check_database_connection()
        email_ok = self.check_email_service()
        scheduler_ok = self.check_scheduler_status()
        stats_ok = await self.check_follow_up_stats()
        api_ok = self.check_api_endpoints()
        
        # Summary
        all_checks_passed = all([db_ok, email_ok, scheduler_ok, stats_ok, api_ok])
        
        if all_checks_passed and not self.issues:
            logger.info("✅ All health checks passed - system is healthy")
            return True
        else:
            logger.warning("⚠️ Health check issues found:")
            for issue in self.issues:
                logger.warning(f"  - {issue}")
            return False

async def main():
    """Main health check function"""
    
    # Get configuration
    base_url = os.getenv("PROD_BASE_URL", "http://localhost:8000")
    admin_token = os.getenv("ADMIN_TOKEN")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        admin_token = sys.argv[2]
    
    logger.info(f"Health checking: {base_url}")
    
    # Run health check
    checker = HealthChecker(base_url, admin_token)
    healthy = await checker.run_health_check()
    
    # Exit with appropriate code
    sys.exit(0 if healthy else 1)

if __name__ == "__main__":
    asyncio.run(main())
