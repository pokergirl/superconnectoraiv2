#!/usr/bin/env python3
"""
Comprehensive Search Functionality Diagnostic Script

This script systematically tests all components of the search functionality
to identify the root causes of the search issues.
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import get_database
from app.core.config import settings
from app.services.retrieval_service import retrieval_service
from app.services.gemini_embeddings_service import gemini_embeddings_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SearchDiagnostics:
    def __init__(self):
        self.db = None
        self.issues_found = []
        self.test_results = {}
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.db = get_database()
            logger.info("✅ Database connection initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {e}")
            self.issues_found.append(f"Database initialization failed: {e}")
            return False
    
    async def test_1_database_connections_count(self):
        """Test 1: Check total connections count and data quality"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 1: DATABASE CONNECTIONS COUNT & QUALITY")
        logger.info("="*60)
        
        try:
            # Total count
            total_count = await self.db.connections.count_documents({})
            logger.info(f"📊 Total connections in database: {total_count}")
            
            if total_count == 0:
                self.issues_found.append("CRITICAL: No connections found in database")
                self.test_results['database_connections'] = {'status': 'FAILED', 'count': 0}
                return False
            
            # Sample connections
            sample_connections = await self.db.connections.find().limit(3).to_list(length=3)
            logger.info(f"📋 Sample connections:")
            for i, conn in enumerate(sample_connections, 1):
                logger.info(f"  {i}. ID: {conn.get('_id')}")
                logger.info(f"     Name: {conn.get('fullName', conn.get('name', 'N/A'))}")
                logger.info(f"     Company: {conn.get('companyName', conn.get('company', 'N/A'))}")
                logger.info(f"     Has user_id: {'user_id' in conn}")
                logger.info(f"     User ID: {conn.get('user_id', 'N/A')}")
            
            # Check user_id distribution
            with_user_id = await self.db.connections.count_documents({"user_id": {"$exists": True}})
            logger.info(f"📈 Connections with user_id: {with_user_id} ({with_user_id/total_count*100:.1f}%)")
            
            if with_user_id == 0:
                self.issues_found.append("CRITICAL: No connections have user_id field - search will fail")
                self.test_results['database_connections'] = {'status': 'FAILED', 'reason': 'No user_id fields'}
                return False
            
            self.test_results['database_connections'] = {
                'status': 'PASSED', 
                'total_count': total_count,
                'with_user_id': with_user_id
            }
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connections test failed: {e}")
            self.issues_found.append(f"Database connections test failed: {e}")
            self.test_results['database_connections'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def test_2_users_exist(self):
        """Test 2: Check if users exist in database"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 2: USERS EXISTENCE CHECK")
        logger.info("="*60)
        
        try:
            total_users = await self.db.users.count_documents({})
            logger.info(f"👥 Total users in database: {total_users}")
            
            if total_users == 0:
                self.issues_found.append("WARNING: No users found in database")
                self.test_results['users_exist'] = {'status': 'WARNING', 'count': 0}
                return False
            
            # Check for test user
            test_user = await self.db.users.find_one({'email': 'test@example.com'})
            if test_user:
                logger.info(f"✅ Test user exists: {test_user['email']} (ID: {test_user['_id']})")
                self.test_results['users_exist'] = {
                    'status': 'PASSED', 
                    'count': total_users,
                    'test_user_id': str(test_user['_id'])
                }
                return True
            else:
                logger.warning("⚠️ Test user does not exist")
                self.test_results['users_exist'] = {'status': 'WARNING', 'count': total_users}
                return False
                
        except Exception as e:
            logger.error(f"❌ Users existence test failed: {e}")
            self.issues_found.append(f"Users existence test failed: {e}")
            self.test_results['users_exist'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def test_3_gemini_configuration(self):
        """Test 3: Check Gemini API configuration and model availability"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 3: GEMINI API CONFIGURATION")
        logger.info("="*60)
        
        try:
            # Check API key
            if not settings.GEMINI_API_KEY:
                self.issues_found.append("CRITICAL: GEMINI_API_KEY not configured")
                self.test_results['gemini_config'] = {'status': 'FAILED', 'reason': 'No API key'}
                return False
            
            logger.info(f"🔑 Gemini API key configured: {settings.GEMINI_API_KEY[:10]}...")
            logger.info(f"🤖 Configured model: {settings.GEMINI_MODEL}")
            
            # Test model availability
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Test with the configured model
            working_model = None
            try:
                logger.info(f"🧪 Testing model: {settings.GEMINI_MODEL}")
                model = genai.GenerativeModel(settings.GEMINI_MODEL)
                response = model.generate_content("Hello")
                if response and response.text:
                    logger.info(f"✅ {settings.GEMINI_MODEL} WORKS!")
                    working_model = settings.GEMINI_MODEL
            except Exception as e:
                logger.warning(f"❌ {settings.GEMINI_MODEL} failed: {str(e)[:100]}")

            if working_model:
                self.test_results['gemini_config'] = {
                    'status': 'PASSED',
                    'configured_model': settings.GEMINI_MODEL,
                    'working_model': working_model
                }
                return True
            else:
                self.issues_found.append(f"CRITICAL: Gemini model '{settings.GEMINI_MODEL}' is not working")
                self.test_results['gemini_config'] = {'status': 'FAILED', 'reason': f"Configured model '{settings.GEMINI_MODEL}' failed"}
                return False
                
        except Exception as e:
            logger.error(f"❌ Gemini configuration test failed: {e}")
            self.issues_found.append(f"Gemini configuration test failed: {e}")
            self.test_results['gemini_config'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def test_4_pinecone_configuration(self):
        """Test 4: Check Pinecone configuration and index status"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 4: PINECONE CONFIGURATION")
        logger.info("="*60)
        
        try:
            if not settings.PINECONE_API_KEY:
                self.issues_found.append("WARNING: PINECONE_API_KEY not configured - will use MongoDB fallback")
                self.test_results['pinecone_config'] = {'status': 'WARNING', 'reason': 'No API key'}
                return False
            
            logger.info(f"🔑 Pinecone API key configured: {settings.PINECONE_API_KEY[:10]}...")
            logger.info(f"📊 Index name: {settings.PINECONE_INDEX_NAME}")
            
            # Test Pinecone connection
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            
            # List indexes
            indexes = pc.list_indexes()
            logger.info(f"📋 Available indexes: {[idx.name for idx in indexes]}")
            
            # Check if our index exists
            index_exists = any(idx.name == settings.PINECONE_INDEX_NAME for idx in indexes)
            if not index_exists:
                self.issues_found.append(f"CRITICAL: Pinecone index '{settings.PINECONE_INDEX_NAME}' does not exist")
                self.test_results['pinecone_config'] = {'status': 'FAILED', 'reason': 'Index not found'}
                return False
            
            # Test index connection
            index = pc.Index(settings.PINECONE_INDEX_NAME)
            stats = index.describe_index_stats()
            logger.info(f"📊 Index stats: {stats}")
            
            self.test_results['pinecone_config'] = {
                'status': 'PASSED',
                'index_name': settings.PINECONE_INDEX_NAME,
                'stats': stats
            }
            return True
            
        except Exception as e:
            logger.error(f"❌ Pinecone configuration test failed: {e}")
            self.issues_found.append(f"Pinecone configuration test failed: {e}")
            self.test_results['pinecone_config'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def test_5_embedding_generation(self):
        """Test 5: Test embedding generation"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 5: EMBEDDING GENERATION")
        logger.info("="*60)
        
        try:
            test_query = "software engineer"
            logger.info(f"🧪 Testing embedding generation for: '{test_query}'")
            
            embedding = await gemini_embeddings_service.generate_embedding(test_query)
            
            if embedding and len(embedding) > 0:
                logger.info(f"✅ Embedding generated successfully: {len(embedding)} dimensions")
                logger.info(f"📊 Sample values: {embedding[:5]}...")
                self.test_results['embedding_generation'] = {
                    'status': 'PASSED',
                    'dimensions': len(embedding)
                }
                return True
            else:
                self.issues_found.append("CRITICAL: Embedding generation returned empty result")
                self.test_results['embedding_generation'] = {'status': 'FAILED', 'reason': 'Empty embedding'}
                return False
                
        except Exception as e:
            logger.error(f"❌ Embedding generation test failed: {e}")
            self.issues_found.append(f"Embedding generation test failed: {e}")
            self.test_results['embedding_generation'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def test_6_mongodb_fallback_search(self):
        """Test 6: Test MongoDB fallback search functionality"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 6: MONGODB FALLBACK SEARCH")
        logger.info("="*60)
        
        try:
            # Get a test user ID
            test_user = await self.db.users.find_one({'email': 'test@example.com'})
            if not test_user:
                logger.warning("⚠️ No test user found, using default user ID")
                user_id = "default_user"
            else:
                user_id = str(test_user['_id'])
            
            logger.info(f"🧪 Testing MongoDB fallback search with user_id: {user_id}")
            
            # Test different queries
            test_queries = ["software engineer", "manager", "developer"]
            
            for query in test_queries:
                logger.info(f"🔍 Testing query: '{query}'")
                
                results = await retrieval_service.fallback_mongodb_search(
                    user_query=query,
                    user_id=user_id,
                    filter_dict=None
                )
                
                logger.info(f"📊 Results for '{query}': {len(results)} profiles")
                
                if results:
                    # Check if results are the same for different queries
                    if query == test_queries[0]:
                        first_query_results = [r.get('id') for r in results]
                    else:
                        current_query_results = [r.get('id') for r in results]
                        if first_query_results == current_query_results:
                            self.issues_found.append(f"CRITICAL: MongoDB fallback returns same results for different queries")
                            logger.warning(f"⚠️ Same results returned for '{test_queries[0]}' and '{query}'")
                
                # Log sample result
                if results:
                    sample = results[0]
                    logger.info(f"📋 Sample result: {sample.get('full_name', 'N/A')} at {sample.get('company_name', 'N/A')}")
            
            if len(results) > 0:
                self.test_results['mongodb_fallback'] = {
                    'status': 'PASSED',
                    'results_count': len(results)
                }
                return True
            else:
                self.issues_found.append("WARNING: MongoDB fallback returned no results")
                self.test_results['mongodb_fallback'] = {'status': 'WARNING', 'reason': 'No results'}
                return False
                
        except Exception as e:
            logger.error(f"❌ MongoDB fallback search test failed: {e}")
            self.issues_found.append(f"MongoDB fallback search test failed: {e}")
            self.test_results['mongodb_fallback'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def test_7_full_search_pipeline(self):
        """Test 7: Test the complete search pipeline"""
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST 7: FULL SEARCH PIPELINE")
        logger.info("="*60)
        
        try:
            # Get a test user ID
            test_user = await self.db.users.find_one({'email': 'test@example.com'})
            if not test_user:
                logger.warning("⚠️ No test user found, using default user ID")
                user_id = "default_user"
            else:
                user_id = str(test_user['_id'])
            
            test_query = "software engineer"
            logger.info(f"🧪 Testing full search pipeline with query: '{test_query}'")
            logger.info(f"👤 User ID: {user_id}")
            
            # Test the complete retrieval and rerank pipeline
            results = await retrieval_service.retrieve_and_rerank(
                user_query=test_query,
                user_id=user_id,
                enable_query_rewrite=True,
                filter_dict=None
            )
            
            logger.info(f"📊 Full pipeline results: {len(results)} profiles")
            
            if results:
                # Log details of first few results
                for i, result in enumerate(results[:3]):
                    profile = result.get('profile', {})
                    logger.info(f"📋 Result {i+1}:")
                    logger.info(f"   Score: {result.get('score', 'N/A')}")
                    logger.info(f"   Name: {profile.get('full_name', 'N/A')}")
                    logger.info(f"   Company: {profile.get('company_name', 'N/A')}")
                    logger.info(f"   Pro: {result.get('pro', 'N/A')}")
                
                self.test_results['full_pipeline'] = {
                    'status': 'PASSED',
                    'results_count': len(results)
                }
                return True
            else:
                self.issues_found.append("CRITICAL: Full search pipeline returned no results")
                self.test_results['full_pipeline'] = {'status': 'FAILED', 'reason': 'No results'}
                return False
                
        except Exception as e:
            logger.error(f"❌ Full search pipeline test failed: {e}")
            self.issues_found.append(f"Full search pipeline test failed: {e}")
            self.test_results['full_pipeline'] = {'status': 'ERROR', 'error': str(e)}
            return False
    
    async def run_all_tests(self):
        """Run all diagnostic tests"""
        logger.info("🚀 Starting comprehensive search diagnostics...")
        logger.info(f"⏰ Started at: {datetime.now()}")
        
        if not await self.initialize():
            return
        
        # Run all tests
        tests = [
            self.test_1_database_connections_count,
            self.test_2_users_exist,
            self.test_3_gemini_configuration,
            self.test_4_pinecone_configuration,
            self.test_5_embedding_generation,
            self.test_6_mongodb_fallback_search,
            self.test_7_full_search_pipeline
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                logger.error(f"❌ Test {test.__name__} crashed: {e}")
                self.issues_found.append(f"Test {test.__name__} crashed: {e}")
        
        # Generate summary report
        await self.generate_summary_report()
    
    async def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        logger.info("\n" + "="*80)
        logger.info("📊 COMPREHENSIVE DIAGNOSTIC SUMMARY REPORT")
        logger.info("="*80)
        
        # Test results summary
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PASSED')
        total_tests = len(self.test_results)
        
        logger.info(f"✅ Tests passed: {passed_tests}/{total_tests}")
        
        # Detailed test results
        logger.info("\n📋 DETAILED TEST RESULTS:")
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            if status == 'PASSED':
                logger.info(f"  ✅ {test_name}: {status}")
            elif status == 'WARNING':
                logger.info(f"  ⚠️ {test_name}: {status}")
            elif status == 'FAILED':
                logger.info(f"  ❌ {test_name}: {status}")
            else:
                logger.info(f"  🔴 {test_name}: {status}")
        
        # Issues found
        if self.issues_found:
            logger.info(f"\n🚨 ISSUES IDENTIFIED ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                logger.info(f"  {i}. {issue}")
        else:
            logger.info("\n🎉 NO CRITICAL ISSUES FOUND!")
        
        # Recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        await self.generate_recommendations()
        
        logger.info(f"\n⏰ Diagnostics completed at: {datetime.now()}")
    
    async def generate_recommendations(self):
        """Generate specific recommendations based on test results"""
        recommendations = []
        
        # Database issues
        if self.test_results.get('database_connections', {}).get('status') == 'FAILED':
            recommendations.append("Import connection data into MongoDB database")
        
        # User issues
        if self.test_results.get('users_exist', {}).get('status') in ['WARNING', 'FAILED']:
            recommendations.append("Create test users for testing search functionality")
        
        # Gemini issues
        gemini_result = self.test_results.get('gemini_config', {})
        if gemini_result.get('status') == 'FAILED':
            recommendations.append("Fix Gemini API configuration and model name")
        elif gemini_result.get('working_model') != gemini_result.get('configured_model'):
            recommendations.append(f"Update GEMINI_MODEL config to use working model: {gemini_result.get('working_model')}")
        
        # Pinecone issues
        if self.test_results.get('pinecone_config', {}).get('status') == 'FAILED':
            recommendations.append("Set up Pinecone index or fix Pinecone configuration")
        
        # Search pipeline issues
        if self.test_results.get('full_pipeline', {}).get('status') == 'FAILED':
            recommendations.append("Debug search pipeline - likely user_id or data association issue")
        
        # MongoDB fallback issues
        if "same results for different queries" in str(self.issues_found):
            recommendations.append("Fix MongoDB fallback query logic to return query-specific results")
        
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"  {i}. {rec}")
        
        if not recommendations:
            logger.info("  🎯 All systems appear to be functioning correctly!")

async def main():
    """Main function to run diagnostics"""
    diagnostics = SearchDiagnostics()
    await diagnostics.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())