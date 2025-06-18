"""
Paperless-ngx API Handler for Warracker

This module provides functionality to interact with Paperless-ngx API
for uploading, retrieving, and managing documents.
"""

import requests
import logging
from typing import Optional, Dict, Any, Tuple
import os
from io import BytesIO

logger = logging.getLogger(__name__)


class PaperlessHandler:
    """Handle interactions with Paperless-ngx API"""
    
    def __init__(self, paperless_url: str, api_token: str):
        """
        Initialize Paperless handler
        
        Args:
            paperless_url: Base URL of Paperless-ngx instance (e.g., https://paperless.example.com)
            api_token: API token for authentication
        """
        self.paperless_url = paperless_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Warracker-PaperlessIntegration/1.0'
        })
        
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Paperless-ngx instance
        
        Returns:
            (success: bool, message: str)
        """
        try:
            response = self.session.get(f'{self.paperless_url}/api/documents/', params={'page_size': 1})
            response.raise_for_status()
            return True, "Connection successful"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to Paperless-ngx instance. Check URL and network connectivity."
        except requests.exceptions.Timeout:
            return False, "Connection timeout. Paperless-ngx instance might be slow or unresponsive."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "Authentication failed. Check your API token."
            elif e.response.status_code == 403:
                return False, "Access forbidden. Check your API token permissions."
            else:
                return False, f"HTTP error: {e.response.status_code} - {e.response.reason}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def upload_document(self, file_content: bytes, filename: str, title: Optional[str] = None, 
                       tags: Optional[list] = None, correspondent: Optional[str] = None) -> Tuple[bool, Optional[int], str]:
        """
        Upload a document to Paperless-ngx
        
        Args:
            file_content: Binary content of the file
            filename: Original filename
            title: Optional title for the document
            tags: Optional list of tag names
            correspondent: Optional correspondent name
            
        Returns:
            (success: bool, document_id: Optional[int], message: str)
        """
        try:
            # Detect MIME type from filename
            import mimetypes
            mime_type, _ = mimetypes.guess_type(filename)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Prepare files for multipart upload
            # Paperless-ngx expects the file under 'document' field
            files = {
                'document': (filename, BytesIO(file_content), mime_type)
            }
            
            # Prepare form data - Paperless-ngx API requirements
            # Note: Don't include 'document' in data, only in files
            data = {}
            if title:
                data['title'] = title
            
            # TODO: For future enhancement, implement proper tag/correspondent handling:
            # - correspondent expects PK (ID) of existing correspondent, not string name
            # - tags expects PKs (IDs) of existing tags, not string names
            # For now, we'll skip these optional fields to get basic upload working
            
            # if correspondent:
            #     # Would need to lookup/create correspondent ID first
            #     data['correspondent'] = correspondent_id
            # if tags:
            #     # Would need to lookup/create tag IDs first
            #     data['tags'] = [tag_id1, tag_id2, ...]
            
            logger.info(f"Uploading document to Paperless-ngx: {filename}")
            logger.info(f"Upload data: {data}")
            logger.info(f"MIME type: {mime_type}")
            
            # Don't set Content-Type manually - let requests handle it
            response = self.session.post(
                f'{self.paperless_url}/api/documents/post_document/',
                files=files,
                headers={'Authorization': f'Token {self.api_token}'},
                timeout=60  # Longer timeout for uploads
            )
            
            logger.info(f"Paperless-ngx upload response status: {response.status_code}")
            logger.info(f"Paperless-ngx upload response text: {response.text[:500]}...")  # First 500 chars
            
            response.raise_for_status()  # This will raise an exception for 4xx/5xx status codes
            
            # Try to parse response as JSON first
            try:
                result = response.json()
                logger.info(f"Paperless-ngx upload response: {result}")
            except Exception as e:
                logger.warning(f"Could not parse response as JSON: {e}")
                # If we can't parse JSON but got 200, treat as success
                return True, None, "Document uploaded successfully"
            
            # Handle different possible response formats from Paperless-ngx
            document_id = None
            if isinstance(result, dict):
                # JSON object response
                if 'task_id' in result:
                    # Task-based response (asynchronous processing)
                    document_id = result.get('task_id')
                    logger.info(f"Document upload task created: {document_id}")
                    return True, document_id, "Document uploaded successfully (processing)"
                elif 'id' in result:
                    # Direct document ID response (synchronous processing)
                    document_id = result.get('id')
                    logger.info(f"Document uploaded with ID: {document_id}")
                    return True, document_id, "Document uploaded successfully"
                elif result.get('success') or response.status_code == 200:
                    # Generic success response
                    logger.info(f"Document uploaded successfully (generic success)")
                    return True, None, "Document uploaded successfully"
                else:
                    logger.warning(f"Unexpected JSON response format from Paperless-ngx: {result}")
                    # Even if format is unexpected, if we got HTTP 200, it's likely successful
                    return True, None, "Document uploaded successfully (unknown JSON format)"
            elif isinstance(result, str):
                # String response - might contain an ID or just be a success message
                logger.info(f"Document uploaded successfully (string response): {result}")
                # Try to extract an ID from the string if it looks like one
                import re
                id_match = re.search(r'\d+', result)
                if id_match:
                    document_id = int(id_match.group())
                    logger.info(f"Extracted document ID from string: {document_id}")
                    return True, document_id, f"Document uploaded successfully: {result}"
                else:
                    return True, None, f"Document uploaded successfully: {result}"
            else:
                # Other response type
                logger.warning(f"Unexpected response type from Paperless-ngx: {type(result)} - {result}")
                return True, None, "Document uploaded successfully (unknown response type)"
                
        except requests.exceptions.Timeout:
            return False, None, "Upload timeout. The file might be too large or the connection is slow."
        except requests.exceptions.HTTPError as e:
            error_msg = f"Upload failed: HTTP {e.response.status_code}"
            try:
                error_detail = e.response.json()
                logger.error(f"Paperless-ngx detailed error: {error_detail}")
                
                if 'detail' in error_detail:
                    error_msg += f" - {error_detail['detail']}"
                elif isinstance(error_detail, dict):
                    # Handle field-specific errors
                    error_parts = []
                    for field, errors in error_detail.items():
                        if isinstance(errors, list):
                            error_parts.append(f"{field}: {', '.join(errors)}")
                        else:
                            error_parts.append(f"{field}: {errors}")
                    if error_parts:
                        error_msg += f" - {'; '.join(error_parts)}"
                else:
                    error_msg += f" - {error_detail}"
            except Exception as parse_error:
                logger.error(f"Could not parse error response: {parse_error}")
                error_msg += f" - {e.response.reason}"
            return False, None, error_msg
        except Exception as e:
            logger.error(f"Error uploading document to Paperless-ngx: {e}")
            return False, None, f"Upload failed: {str(e)}"
    
    def get_document_preview(self, document_id: int) -> Tuple[bool, Optional[bytes], str, Optional[str]]:
        """
        Get document preview/content from Paperless-ngx
        
        Args:
            document_id: Paperless-ngx document ID
            
        Returns:
            (success: bool, content: Optional[bytes], message: str, content_type: Optional[str])
        """
        # Try multiple endpoints in order of preference
        endpoints_to_try = [
            ('preview', f'/api/documents/{document_id}/preview/'),
            ('download', f'/api/documents/{document_id}/download/'),
        ]
        
        last_error = None
        
        for endpoint_name, endpoint_path in endpoints_to_try:
            try:
                logger.info(f"Fetching document {endpoint_name} from Paperless-ngx: {document_id}")
                response = self.session.get(
                    f'{self.paperless_url}{endpoint_path}',
                    timeout=30
                )
                
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', 'application/octet-stream')
                logger.info(f"Successfully retrieved document {document_id} via {endpoint_name} endpoint")
                return True, response.content, f"Document retrieved successfully via {endpoint_name}", content_type
                
            except requests.exceptions.HTTPError as e:
                logger.warning(f"Failed to retrieve document {document_id} via {endpoint_name}: HTTP {e.response.status_code}")
                last_error = e
                if e.response.status_code == 404:
                    continue  # Try next endpoint
                else:
                    # For non-404 errors, don't try other endpoints
                    return False, None, f"Failed to retrieve document: HTTP {e.response.status_code}", None
            except Exception as e:
                logger.warning(f"Error retrieving document {document_id} via {endpoint_name}: {e}")
                last_error = e
                continue  # Try next endpoint
        
        # If we get here, all endpoints failed
        if last_error and isinstance(last_error, requests.exceptions.HTTPError) and last_error.response.status_code == 404:
            return False, None, "Document not found in Paperless-ngx", None
        else:
            return False, None, f"Retrieval failed: {str(last_error) if last_error else 'All endpoints failed'}", None
    
    def get_document_thumbnail(self, document_id: int) -> Tuple[bool, Optional[bytes], str]:
        """
        Get document thumbnail from Paperless-ngx
        
        Args:
            document_id: Paperless-ngx document ID
            
        Returns:
            (success: bool, content: Optional[bytes], message: str)
        """
        try:
            response = self.session.get(
                f'{self.paperless_url}/api/documents/{document_id}/thumb/',
                timeout=15
            )
            
            response.raise_for_status()
            return True, response.content, "Thumbnail retrieved successfully"
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False, None, "Document or thumbnail not found"
            else:
                return False, None, f"Failed to retrieve thumbnail: HTTP {e.response.status_code}"
        except Exception as e:
            logger.error(f"Error retrieving thumbnail from Paperless-ngx: {e}")
            return False, None, f"Thumbnail retrieval failed: {str(e)}"
    
    def search_documents(self, query: str, limit: int = 25) -> Tuple[bool, Optional[list], str]:
        """
        Search documents in Paperless-ngx
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            (success: bool, documents: Optional[list], message: str)
        """
        try:
            params = {
                'query': query,
                'page_size': min(limit, 100)  # Cap at 100 for performance
            }
            
            response = self.session.get(
                f'{self.paperless_url}/api/documents/',
                params=params,
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            
            documents = result.get('results', [])
            return True, documents, f"Found {len(documents)} documents"
            
        except Exception as e:
            logger.error(f"Error searching documents in Paperless-ngx: {e}")
            return False, None, f"Search failed: {str(e)}"
    
    def get_document_info(self, document_id: int) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Get document information from Paperless-ngx
        
        Args:
            document_id: Paperless-ngx document ID
            
        Returns:
            (success: bool, document_info: Optional[Dict], message: str)
        """
        try:
            response = self.session.get(
                f'{self.paperless_url}/api/documents/{document_id}/',
                timeout=15
            )
            
            response.raise_for_status()
            document_info = response.json()
            
            return True, document_info, "Document info retrieved successfully"
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False, None, "Document not found"
            else:
                return False, None, f"Failed to retrieve document info: HTTP {e.response.status_code}"
        except Exception as e:
            logger.error(f"Error retrieving document info from Paperless-ngx: {e}")
            return False, None, f"Info retrieval failed: {str(e)}"

    def debug_document_status(self, document_id: int) -> Dict[str, Any]:
        """
        Debug method to check document status and available endpoints
        
        Args:
            document_id: Paperless-ngx document ID
            
        Returns:
            Dictionary with debug information
        """
        debug_info = {
            'document_id': document_id,
            'endpoints_tested': {},
            'document_exists': False,
            'document_info': None
        }
        
        # Test different endpoints
        endpoints_to_test = [
            ('info', f'/api/documents/{document_id}/'),
            ('preview', f'/api/documents/{document_id}/preview/'),
            ('download', f'/api/documents/{document_id}/download/'),
            ('thumb', f'/api/documents/{document_id}/thumb/')
        ]
        
        for endpoint_name, endpoint_path in endpoints_to_test:
            try:
                logger.info(f"Testing endpoint: {self.paperless_url}{endpoint_path}")
                response = self.session.get(f'{self.paperless_url}{endpoint_path}', timeout=15)
                
                debug_info['endpoints_tested'][endpoint_name] = {
                    'status_code': response.status_code,
                    'success': response.status_code < 400,
                    'content_type': response.headers.get('Content-Type', 'unknown'),
                    'content_length': len(response.content) if response.content else 0
                }
                
                if endpoint_name == 'info' and response.status_code == 200:
                    debug_info['document_exists'] = True
                    try:
                        debug_info['document_info'] = response.json()
                    except:
                        debug_info['document_info'] = 'Could not parse JSON'
                        
            except Exception as e:
                debug_info['endpoints_tested'][endpoint_name] = {
                    'error': str(e),
                    'success': False
                }
        
        # Also try to list recent documents to see if our document is there
        try:
            response = self.session.get(f'{self.paperless_url}/api/documents/', 
                                      params={'ordering': '-created', 'page_size': 10}, 
                                      timeout=15)
            if response.status_code == 200:
                recent_docs = response.json().get('results', [])
                debug_info['recent_documents'] = [
                    {'id': doc.get('id'), 'title': doc.get('title'), 'created': doc.get('created')}
                    for doc in recent_docs
                ]
                debug_info['document_in_recent'] = any(doc.get('id') == document_id for doc in recent_docs)
            else:
                debug_info['recent_documents'] = f'Error: {response.status_code}'
        except Exception as e:
            debug_info['recent_documents'] = f'Exception: {str(e)}'
        
        return debug_info

    def document_exists(self, document_id: int) -> bool:
        """
        Check if a document exists in Paperless-ngx
        
        Args:
            document_id: Paperless-ngx document ID
            
        Returns:
            True if document exists, False otherwise
        """
        try:
            response = self.session.get(
                f'{self.paperless_url}/api/documents/{document_id}/',
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Error checking document existence {document_id}: {e}")
            return False


def get_paperless_handler(conn) -> Optional[PaperlessHandler]:
    """
    Get a configured Paperless handler from site settings
    
    Args:
        conn: Database connection
        
    Returns:
        PaperlessHandler instance or None if not configured/enabled
    """
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT key, value FROM site_settings 
                WHERE key IN ('paperless_enabled', 'paperless_url', 'paperless_api_token')
            """)
            settings = {row[0]: row[1] for row in cur.fetchall()}
            
            # Check if Paperless-ngx is enabled
            if settings.get('paperless_enabled', 'false').lower() != 'true':
                return None
            
            # Check required settings
            paperless_url = settings.get('paperless_url', '').strip()
            paperless_token = settings.get('paperless_api_token', '').strip()
            
            if not paperless_url or not paperless_token:
                logger.warning("Paperless-ngx is enabled but URL or API token is missing")
                return None
            
            return PaperlessHandler(paperless_url, paperless_token)
            
    except Exception as e:
        logger.error(f"Error creating Paperless handler: {e}")
        return None 