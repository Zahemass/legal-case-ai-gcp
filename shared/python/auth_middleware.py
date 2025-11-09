"""
Authentication and Authorization Middleware for Legal Case AI - Python Implementation
Handles Firebase Auth token validation and user authorization for Python services
"""

import os
import logging
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import json
from datetime import datetime, timezone
import time

import firebase_admin
from firebase_admin import credentials, auth
from google.cloud import firestore

from .firestore_client import FirestoreClient

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication and Authorization middleware for Python services"""
    
    def __init__(self):
        # Initialize Firebase Admin if not already initialized
        if not firebase_admin._apps:
            service_account_key = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
            project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('FIREBASE_PROJECT_ID')
            
            if service_account_key:
                # Initialize with service account key
                service_account = json.loads(service_account_key)
                cred = credentials.Certificate(service_account)
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
            else:
                # Initialize with default credentials (for GCP environments)
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
        
        self.firestore_client = FirestoreClient()
        
        # Role hierarchy for authorization
        self.role_hierarchy = {
            'super_admin': 5,
            'admin': 4,
            'legal_professional': 3,
            'paralegal': 2,
            'user': 1,
            'guest': 0
        }
        
        # Rate limiting storage
        self.rate_limit_storage = {}
        
        logger.info("✅ AuthMiddleware initialized")

    def verify_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Firebase ID token and return user info"""
        try:
            if not id_token:
                raise ValueError("ID token is required")
            
            # Verify the ID token
            decoded_token = auth.verify_id_token(id_token)
            
            # Create user info object
            user_info = {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'email_verified': decoded_token.get('email_verified', False),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'role': decoded_token.get('role', 'user'),
                'auth_time': decoded_token.get('auth_time'),
                'firebase': decoded_token
            }
            
            # Update user's last login time
            self._update_user_login_time(user_info['uid'])
            
            logger.info(f"✅ User authenticated: {user_info['uid']} ({user_info['email']})")
            return user_info
            
        except Exception as e:
            logger.error(f"❌ Token verification failed: {e}")
            raise

    def verify_api_key(self, api_key: str) -> bool:
        """Verify API key for service-to-service communication"""
        try:
            expected_api_key = os.environ.get('INTERNAL_API_KEY')
            
            if not expected_api_key:
                logger.warning("⚠️ INTERNAL_API_KEY not set, skipping API key validation")
                return True
            
            if not api_key:
                raise ValueError("API key is required")
            
            if api_key != expected_api_key:
                raise ValueError("Invalid API key")
            
            logger.info("✅ API key validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ API key validation failed: {e}")
            raise

    def has_role(self, user_role: str, required_role: str) -> bool:
        """Check if user has specific role (with hierarchy)"""
        user_level = self.role_hierarchy.get(user_role, 0)
        required_level = self.role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level

    def check_case_access(self, user_id: str, case_id: str, user_role: str = 'user') -> bool:
        """Check if user has access to specific case"""
        try:
            # Get case to check ownership
            case_data = self.firestore_client.get_case(case_id)
            
            if not case_data:
                return False
            
            # Check if user is the case owner or has admin role
            if case_data.get('createdBy') == user_id or self.has_role(user_role, 'admin'):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Case access check failed: {e}")
            return False

    def check_rate_limit(self, identifier: str, max_requests: int = 100, window_minutes: int = 15) -> bool:
        """Check rate limit for user or IP"""
        try:
            now = time.time()
            window_start = now - (window_minutes * 60)
            
            # Clean old entries
            if identifier in self.rate_limit_storage:
                self.rate_limit_storage[identifier] = [
                    timestamp for timestamp in self.rate_limit_storage[identifier]
                    if timestamp > window_start
                ]
            else:
                self.rate_limit_storage[identifier] = []
            
            # Check if limit exceeded
            if len(self.rate_limit_storage[identifier]) >= max_requests:
                return False
            
            # Add current request
            self.rate_limit_storage[identifier].append(now)
            
            # Periodic cleanup (1% chance)
            if len(self.rate_limit_storage) > 1000 and time.time() % 100 < 1:
                self._cleanup_rate_limit(window_start)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {e}")
            return True  # Allow on error

    # ==================== DECORATORS ====================

    def require_auth(self, f: Callable) -> Callable:
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Extract token from various sources
                id_token = self._extract_token_from_request(*args, **kwargs)
                
                if not id_token:
                    raise ValueError("Authentication token required")
                
                # Verify token
                user_info = self.verify_token(id_token)
                
                # Add user info to kwargs
                kwargs['current_user'] = user_info
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"❌ Authentication failed: {e}")
                raise
        
        return decorated_function

    def require_role(self, required_role: str) -> Callable:
        """Decorator to require specific role"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    current_user = kwargs.get('current_user')
                    
                    if not current_user:
                        raise ValueError("Authentication required")
                    
                    # Get user profile to check role
                    user_profile = self.firestore_client.get_user_profile(current_user['uid'])
                    
                    if not user_profile:
                        raise ValueError("User profile not found")
                    
                    user_role = user_profile.get('role', 'user')
                    
                    # Check role hierarchy
                    if not self.has_role(user_role, required_role):
                        raise ValueError(f"Insufficient permissions. Required role: {required_role}")
                    
                    # Add role to user info
                    current_user['role'] = user_role
                    
                    logger.info(f"✅ Role check passed: {current_user['uid']} has role {user_role}")
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"❌ Role check failed: {e}")
                    raise
            
            return decorated_function
        return decorator

    def require_case_access(self, f: Callable) -> Callable:
        """Decorator to require case access"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                current_user = kwargs.get('current_user')
                
                if not current_user:
                    raise ValueError("Authentication required")
                
                # Extract case ID from args or kwargs
                case_id = self._extract_case_id(*args, **kwargs)
                
                if not case_id:
                    raise ValueError("Case ID required")
                
                # Get user role
                user_profile = self.firestore_client.get_user_profile(current_user['uid'])
                user_role = user_profile.get('role', 'user') if user_profile else 'user'
                
                # Check case access
                if not self.check_case_access(current_user['uid'], case_id, user_role):
                    raise ValueError("Access denied to this case")
                
                # Add case info to kwargs
                case_data = self.firestore_client.get_case(case_id)
                kwargs['current_case'] = case_data
                
                logger.info(f"✅ Case access granted: {current_user['uid']} -> {case_id}")
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"❌ Case access check failed: {e}")
                raise
        
        return decorated_function

    def rate_limit(self, max_requests: int = 100, window_minutes: int = 15) -> Callable:
        """Decorator for rate limiting"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                try:
                    current_user = kwargs.get('current_user')
                    
                    # Use user ID if available, otherwise use a generic identifier
                    identifier = current_user['uid'] if current_user else 'anonymous'
                    
                    if not self.check_rate_limit(identifier, max_requests, window_minutes):
                        raise ValueError("Rate limit exceeded")
                    
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    if "Rate limit exceeded" in str(e):
                        logger.warning(f"⚠️ Rate limit exceeded for {identifier}")
                    else:
                        logger.error(f"❌ Rate limiting error: {e}")
                    raise
            
            return decorated_function
        return decorator

    def validate_api_key(self, f: Callable) -> Callable:
        """Decorator to validate API key"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Extract API key from args or kwargs
                api_key = self._extract_api_key(*args, **kwargs)
                
                if not self.verify_api_key(api_key):
                    raise ValueError("Invalid API key")
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"❌ API key validation failed: {e}")
                raise
        
        return decorated_function

    # ==================== USER MANAGEMENT ====================

    def create_custom_token(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Create custom token for user"""
        try:
            custom_token = auth.create_custom_token(user_id, additional_claims)
            logger.info(f"✅ Custom token created for user: {user_id}")
            return custom_token.decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Error creating custom token for {user_id}: {e}")
            raise

    def revoke_refresh_tokens(self, user_id: str) -> bool:
        """Revoke refresh tokens for user"""
        try:
            auth.revoke_refresh_tokens(user_id)
            logger.info(f"✅ Refresh tokens revoked for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error revoking tokens for {user_id}: {e}")
            raise

    def set_custom_user_claims(self, user_id: str, custom_claims: Dict[str, Any]) -> bool:
        """Set custom user claims"""
        try:
            auth.set_custom_user_claims(user_id, custom_claims)
            logger.info(f"✅ Custom claims set for user: {user_id}", custom_claims)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting custom claims for {user_id}: {e}")
            raise

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            user_record = auth.get_user_by_email(email)
            
            return {
                'uid': user_record.uid,
                'email': user_record.email,
                'email_verified': user_record.email_verified,
                'display_name': user_record.display_name,
                'photo_url': user_record.photo_url,
                'disabled': user_record.disabled,
                'creation_timestamp': user_record.user_metadata.creation_timestamp,
                'last_sign_in_timestamp': user_record.user_metadata.last_sign_in_timestamp
            }
            
        except auth.UserNotFoundError:
            return None
        except Exception as e:
            logger.error(f"❌ Error getting user by email {email}: {e}")
            raise

    def disable_user(self, user_id: str) -> bool:
        """Disable user account"""
        try:
            auth.update_user(user_id, disabled=True)
            logger.info(f"✅ User account disabled: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error disabling user {user_id}: {e}")
            raise

    def enable_user(self, user_id: str) -> bool:
        """Enable user account"""
        try:
            auth.update_user(user_id, disabled=False)
            logger.info(f"✅ User account enabled: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enabling user {user_id}: {e}")
            raise

    # ==================== UTILITY METHODS ====================

    def _extract_token_from_request(self, *args, **kwargs) -> Optional[str]:
        """Extract token from request arguments"""
        # Check kwargs first
        if 'auth_token' in kwargs:
            return kwargs['auth_token']
        
        if 'id_token' in kwargs:
            return kwargs['id_token']
        
        # Check if there's a request-like object in args
        for arg in args:
            if hasattr(arg, 'headers'):
                auth_header = arg.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    return auth_header.split('Bearer ')[1]
            
            if hasattr(arg, 'get'):
                # Could be a request object or dict
                auth_header = arg.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    return auth_header.split('Bearer ')[1]
        
        return None

    def _extract_case_id(self, *args, **kwargs) -> Optional[str]:
        """Extract case ID from arguments"""
        # Check kwargs
        if 'case_id' in kwargs:
            return kwargs['case_id']
        
        if 'caseId' in kwargs:
            return kwargs['caseId']
        
        # Check positional args for case_id
        for arg in args:
            if isinstance(arg, str) and len(arg) > 10:  # Likely a UUID
                return arg
            
            if isinstance(arg, dict) and 'caseId' in arg:
                return arg['caseId']
        
        return None

    def _extract_api_key(self, *args, **kwargs) -> Optional[str]:
        """Extract API key from arguments"""
        # Check kwargs
        if 'api_key' in kwargs:
            return kwargs['api_key']
        
        # Check headers if available
        for arg in args:
            if hasattr(arg, 'headers'):
                return arg.headers.get('X-API-Key')
            
            if hasattr(arg, 'get'):
                return arg.get('X-API-Key')
        
        return None

    def _update_user_login_time(self, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Update user's last login time"""
        try:
            if metadata is None:
                metadata = {}
            
            self.firestore_client.save_user_profile({
                'uid': user_id,
                'lastLoginAt': datetime.now(timezone.utc),
                'metadata': {
                    **metadata,
                    'lastLoginTimestamp': time.time()
                }
            })
            
            # Log login activity
            self.firestore_client.log_user_activity(user_id, 'user_login', metadata)
            
        except Exception as e:
            logger.error(f"❌ Failed to update user login time: {e}")
            # Don't raise error as this is not critical

    def _cleanup_rate_limit(self, window_start: float):
        """Clean up old rate limit entries"""
        try:
            for identifier in list(self.rate_limit_storage.keys()):
                self.rate_limit_storage[identifier] = [
                    timestamp for timestamp in self.rate_limit_storage[identifier]
                    if timestamp > window_start
                ]
                
                if not self.rate_limit_storage[identifier]:
                    del self.rate_limit_storage[identifier]
                    
        except Exception as e:
            logger.error(f"❌ Rate limit cleanup error: {e}")

    # ==================== CONTEXT MANAGERS ====================

    class AuthContext:
        """Context manager for authentication"""
        
        def __init__(self, auth_middleware, id_token: str):
            self.auth_middleware = auth_middleware
            self.id_token = id_token
            self.user_info = None

        def __enter__(self):
            self.user_info = self.auth_middleware.verify_token(self.id_token)
            return self.user_info

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Cleanup if needed
            pass

    def authenticated_context(self, id_token: str):
        """Create authenticated context"""
        return self.AuthContext(self, id_token)

    # ==================== VALIDATION HELPERS ====================

    def validate_user_permissions(self, user_id: str, required_permissions: List[str]) -> bool:
        """Validate user has required permissions"""
        try:
            user_profile = self.firestore_client.get_user_profile(user_id)
            
            if not user_profile:
                return False
            
            user_permissions = user_profile.get('permissions', [])
            user_role = user_profile.get('role', 'user')
            
            # Admin users have all permissions
            if self.has_role(user_role, 'admin'):
                return True
            
            # Check specific permissions
            for permission in required_permissions:
                if permission not in user_permissions:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Permission validation failed: {e}")
            return False

    def is_user_active(self, user_id: str) -> bool:
        """Check if user account is active"""
        try:
            user_profile = self.firestore_client.get_user_profile(user_id)
            
            if not user_profile:
                return False
            
            return user_profile.get('isActive', True)
            
        except Exception as e:
            logger.error(f"❌ User active check failed: {e}")
            return False

    def get_user_role(self, user_id: str) -> str:
        """Get user role"""
        try:
            user_profile = self.firestore_client.get_user_profile(user_id)
            
            if not user_profile:
                return 'user'
            
            return user_profile.get('role', 'user')
            
        except Exception as e:
            logger.error(f"❌ Get user role failed: {e}")
            return 'user'