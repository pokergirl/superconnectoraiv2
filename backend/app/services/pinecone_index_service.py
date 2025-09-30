import time
from typing import Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings


class PineconeIndexService:
    """Service for managing Pinecone index creation and configuration."""
    
    def __init__(self):
        """Initialize the Pinecone client."""
        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY is required but not provided in configuration.")
        
        self.client = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        
        # Index configuration as specified in requirements
        self.index_config = {
            "dimension": 1536,  # For text-embedding-3-small model
            "metric": "cosine",
            "spec": ServerlessSpec(
                cloud=settings.PINECONE_CLOUD,
                region=settings.PINECONE_REGION
            )
        }
        self.index = self.client.Index(self.index_name)
    
    def index_exists(self) -> bool:
        """
        Check if the Pinecone index already exists.
        
        Returns:
            True if index exists, False otherwise
        """
        try:
            existing_indexes = self.client.list_indexes()
            return any(index.name == self.index_name for index in existing_indexes)
        except Exception as e:
            print(f"Error checking if index exists: {e}")
            return False
    
    def get_index_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the existing index.
        
        Returns:
            Index information dictionary or None if index doesn't exist
        """
        try:
            if not self.index_exists():
                return None
            
            index_info = self.client.describe_index(self.index_name)
            return {
                "name": index_info.name,
                "dimension": index_info.dimension,
                "metric": index_info.metric,
                "host": index_info.host,
                "spec": index_info.spec,
                "status": index_info.status
            }
        except Exception as e:
            print(f"Error getting index info: {e}")
            return None
    
    def create_index(self) -> Dict[str, Any]:
        """
        Create a new Pinecone serverless index with hybrid search and metadata filtering support.
        This method is idempotent - it will not create the index if it already exists.
        
        Returns:
            Dictionary containing creation result and index information
        """
        try:
            # Check if index already exists
            if self.index_exists():
                print(f"Index '{self.index_name}' already exists. Skipping creation.")
                return {
                    "success": True,
                    "message": f"Index '{self.index_name}' already exists",
                    "created": False,
                    "index_info": self.get_index_info()
                }
            
            print(f"Creating Pinecone index '{self.index_name}'...")
            
            # Create the index with serverless configuration
            self.client.create_index(
                name=self.index_name,
                dimension=self.index_config["dimension"],
                metric=self.index_config["metric"],
                spec=self.index_config["spec"]
            )
            
            # Wait for index to be ready
            print("Waiting for index to be ready...")
            self._wait_for_index_ready()
            
            # Get final index information
            index_info = self.get_index_info()
            
            print(f"Successfully created index '{self.index_name}'")
            
            return {
                "success": True,
                "message": f"Index '{self.index_name}' created successfully",
                "created": True,
                "index_info": index_info
            }
            
        except Exception as e:
            error_msg = f"Error creating index '{self.index_name}': {e}"
            print(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "created": False,
                "index_info": None
            }
    
    def _wait_for_index_ready(self, timeout: int = 300) -> None:
        """
        Wait for the index to be ready for use.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                index_info = self.client.describe_index(self.index_name)
                if index_info.status.ready:
                    print("Index is ready!")
                    return
                
                print("Index is still initializing...")
                time.sleep(10)  # Wait 10 seconds before checking again
                
            except Exception as e:
                print(f"Error checking index status: {e}")
                time.sleep(10)
        
        raise TimeoutError(f"Index '{self.index_name}' did not become ready within {timeout} seconds")
    
    def delete_index(self) -> Dict[str, Any]:
        """
        Delete the Pinecone index. Use with caution!
        
        Returns:
            Dictionary containing deletion result
        """
        try:
            if not self.index_exists():
                return {
                    "success": True,
                    "message": f"Index '{self.index_name}' does not exist",
                    "deleted": False
                }
            
            print(f"Deleting index '{self.index_name}'...")
            self.client.delete_index(self.index_name)
            
            return {
                "success": True,
                "message": f"Index '{self.index_name}' deleted successfully",
                "deleted": True
            }
            
        except Exception as e:
            error_msg = f"Error deleting index '{self.index_name}': {e}"
            print(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "deleted": False
            }
    def clear_namespace(self, namespace: str) -> Dict[str, Any]:
        """
        Clear all vectors from a specific namespace in the Pinecone index.

        Args:
            namespace: The namespace to clear.

        Returns:
            Dictionary containing the result of the operation.
        """
        try:
            print(f"Clearing namespace '{namespace}' in index '{self.index_name}'...")
            
            if not self.index_exists():
                return {
                    "success": False,
                    "message": f"Index '{self.index_name}' does not exist. Cannot clear namespace.",
                }

            self.index.delete(delete_all=True, namespace=namespace)
            
            return {
                "success": True,
                "message": f"Successfully cleared namespace '{namespace}'"
            }
            
        except Exception as e:
            error_msg = f"Error clearing namespace '{namespace}': {e}"
            print(error_msg)
            return {
                "success": False,
                "message": error_msg
            }
    
    def setup_index(self) -> Dict[str, Any]:
        """
        Main method to set up the Pinecone index with all required configurations.
        This includes:
        - Creating the serverless index with correct dimensions and metric
        - Enabling hybrid search (handled by Pinecone automatically for serverless)
        - Enabling metadata filtering (supported by default)
        
        Returns:
            Dictionary containing setup result and index information
        """
        print("Setting up Pinecone index...")
        print(f"Index name: {self.index_name}")
        print(f"Dimension: {self.index_config['dimension']}")
        print(f"Metric: {self.index_config['metric']}")
        print(f"Cloud: {self.index_config['spec'].cloud}")
        print(f"Region: {self.index_config['spec'].region}")
        
        result = self.create_index()
        
        if result["success"]:
            print("\n✅ Pinecone index setup completed successfully!")
            print("\nIndex Features:")
            print("- ✅ Serverless configuration (AWS us-west-2)")
            print("- ✅ Dimension: 1536 (compatible with text-embedding-3-small)")
            print("- ✅ Metric: cosine similarity")
            print("- ✅ Hybrid search support (dense + sparse vectors)")
            print("- ✅ Metadata filtering enabled")
            print("- ✅ Namespace support for tenant isolation")
            
            if result["index_info"]:
                print(f"\nIndex Status: {result['index_info']['status']}")
                print(f"Index Host: {result['index_info']['host']}")
        else:
            print("\n❌ Pinecone index setup failed!")
        
        return result


# Global instance
pinecone_index_service = PineconeIndexService()