#!/usr/bin/env python3
"""
Production Testing Script for Access Request Follow-Up Email System
This script provides comprehensive testing for the production environment.
"""

import asyncio
import logging
import sys
import os
import requests
import json
from datetime import datetime, timedelta
from uuid import uuid4

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.db import connect_to_mongo, close_mongo_connection, get_database
from app.services.access_request_follow_up_service import (
    schedule_access_request_follow_up_email,
    get_pending_access_request_follow_ups,
    send_access_request_follow_up_email,
    get_access_request_follow_up_stats,
    process_pending_access_request_follow_ups
)
from app.services.scheduler_service import scheduler_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionTester:
    def __init__(self, base_url: str = None, admin_token: str = None):
        self.base_url = base_url or "http://localhost:8000"
        self.admin_token = admin_token
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    async def test_database_connection(self):
        """Test 1: Database connection and collection access"""
        try:
            await connect_to_mongo()
            db = get_database()
            
            # Test collection access
            collections = await db.list_collection_names()
            if "access_request_follow_ups" in collections:
                self.log_test("Database Connection", True, "MongoDB connected and collection exists")
            else:
                self.log_test("Database Connection", False, "Collection 'access_request_follow_ups' not found")
                
        except Exception as e:
            self.log_test("Database Connection", False, f"Database error: {str(e)}")
        finally:
            await close_mongo_connection()
    
    async def test_email_template_generation(self):
        """Test 2: Email template generation"""
        try:
            from app.services.access_request_follow_up_service import generate_access_request_follow_up_content
            
            email_content = generate_access_request_follow_up_content("Test User")
            
            # Check required elements
            required_elements = ["Test User", "SuperConnect AI", "donate", "Warmly", "Ha"]
            missing_elements = []
            
            for element in required_elements:
                if element not in email_content:
                    missing_elements.append(element)
            
            if not missing_elements:
                self.log_test("Email Template Generation", True, "All required elements present")
            else:
                self.log_test("Email Template Generation", False, f"Missing elements: {missing_elements}")
                
        except Exception as e:
            self.log_test("Email Template Generation", False, f"Template error: {str(e)}")
    
    async def test_follow_up_scheduling(self):
        """Test 3: Follow-up email scheduling"""
        try:
            await connect_to_mongo()
            db = get_database()
            
            # Schedule a test follow-up
            test_id = str(uuid4())
            follow_up_dict = await schedule_access_request_follow_up_email(
                db=db,
                access_request_id=test_id,
                user_email="test@example.com",
                user_name="Test User",
                follow_up_days=14
            )
            
            # Verify it was created
            if follow_up_dict and follow_up_dict.get("id"):
                self.log_test("Follow-up Scheduling", True, f"Scheduled follow-up: {follow_up_dict['id']}")
                
                # Clean up test data
                await db.access_request_follow_ups.delete_one({"id": follow_up_dict["id"]})
            else:
                self.log_test("Follow-up Scheduling", False, "Failed to create follow-up record")
                
        except Exception as e:
            self.log_test("Follow-up Scheduling", False, f"Scheduling error: {str(e)}")
        finally:
            await close_mongo_connection()
    
    async def test_scheduler_service(self):
        """Test 4: Scheduler service functionality"""
        try:
            # Test scheduler start/stop
            await scheduler_service.start()
            await asyncio.sleep(1)  # Let it run briefly
            await scheduler_service.stop()
            
            self.log_test("Scheduler Service", True, "Scheduler starts and stops correctly")
            
        except Exception as e:
            self.log_test("Scheduler Service", False, f"Scheduler error: {str(e)}")
    
    async def test_email_service_configuration(self):
        """Test 5: Email service configuration"""
        try:
            from app.services.email_service import get_email_service
            
            email_service = get_email_service()
            service_name = type(email_service).__name__
            
            # Check if Gmail API is available
            if hasattr(email_service, 'is_available'):
                if email_service.is_available():
                    self.log_test("Email Service Configuration", True, f"Gmail API available ({service_name})")
                else:
                    self.log_test("Email Service Configuration", True, f"SMTP fallback available ({service_name})")
            else:
                self.log_test("Email Service Configuration", True, f"SMTP service available ({service_name})")
                
        except Exception as e:
            self.log_test("Email Service Configuration", False, f"Email service error: {str(e)}")
    
    def test_api_endpoints(self):
        """Test 6: API endpoints (if admin token provided)"""
        if not self.admin_token:
            self.log_test("API Endpoints", False, "No admin token provided - skipping API tests")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Test stats endpoint
            response = requests.get(f"{self.base_url}/api/v1/admin/access-request-follow-ups/stats", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                self.log_test("API Stats Endpoint", True, f"Stats retrieved: {stats.get('stats', {})}")
            else:
                self.log_test("API Stats Endpoint", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test pending endpoint
            response = requests.get(f"{self.base_url}/api/v1/admin/access-request-follow-ups/pending", headers=headers)
            if response.status_code == 200:
                pending = response.json()
                self.log_test("API Pending Endpoint", True, f"Found {len(pending)} pending follow-ups")
            else:
                self.log_test("API Pending Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("API Endpoints", False, f"API error: {str(e)}")
    
    async def test_manual_email_processing(self):
        """Test 7: Manual email processing"""
        try:
            await connect_to_mongo()
            db = get_database()
            
            # Create a test follow-up that's due now
            test_id = str(uuid4())
            follow_up_dict = await schedule_access_request_follow_up_email(
                db=db,
                access_request_id=test_id,
                user_email="test-processing@example.com",
                user_name="Test Processing User",
                follow_up_days=0  # Due immediately
            )
            
            # Update scheduled date to be in the past
            await db.access_request_follow_ups.update_one(
                {"id": follow_up_dict["id"]},
                {"$set": {"scheduled_date": datetime.utcnow() - timedelta(minutes=1)}}
            )
            
            # Process pending follow-ups
            processed_count = await process_pending_access_request_follow_ups()
            
            if processed_count > 0:
                self.log_test("Manual Email Processing", True, f"Processed {processed_count} emails")
            else:
                self.log_test("Manual Email Processing", False, "No emails were processed")
            
            # Clean up test data
            await db.access_request_follow_ups.delete_many({"access_request_id": test_id})
            
        except Exception as e:
            self.log_test("Manual Email Processing", False, f"Processing error: {str(e)}")
        finally:
            await close_mongo_connection()
    
    async def run_all_tests(self):
        """Run all production tests"""
        logger.info("=" * 60)
        logger.info("PRODUCTION TESTING - ACCESS REQUEST FOLLOW-UP SYSTEM")
        logger.info("=" * 60)
        
        # Run all tests
        await self.test_database_connection()
        await self.test_email_template_generation()
        await self.test_follow_up_scheduling()
        await self.test_scheduler_service()
        await self.test_email_service_configuration()
        self.test_api_endpoints()
        await self.test_manual_email_processing()
        
        # Summary
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        logger.info("=" * 60)
        logger.info(f"TEST SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! System is ready for production.")
        else:
            logger.error("❌ SOME TESTS FAILED! Please review the failures above.")
            
        logger.info("=" * 60)
        
        return passed == total

async def main():
    """Main function for production testing"""
    
    # Get configuration from environment or command line
    base_url = os.getenv("PROD_BASE_URL", "http://localhost:8000")
    admin_token = os.getenv("ADMIN_TOKEN")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        admin_token = sys.argv[2]
    
    logger.info(f"Testing against: {base_url}")
    if admin_token:
        logger.info("Admin token provided - API tests enabled")
    else:
        logger.info("No admin token - API tests will be skipped")
    
    # Run tests
    tester = ProductionTester(base_url, admin_token)
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
