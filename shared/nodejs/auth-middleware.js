// shared/nodejs/auth-middleware.js
const admin = require('firebase-admin');
const FirestoreClient = require('./firestore-client');

/**
 * Authentication and Authorization Middleware for Legal Case AI
 * Handles Firebase Auth token validation and user authorization
 */
class AuthMiddleware {
  constructor() {
    // Initialize Firebase Admin if not already initialized
    if (!admin.apps.length) {
      const serviceAccountKey = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
      const projectId = process.env.GOOGLE_CLOUD_PROJECT || process.env.FIREBASE_PROJECT_ID;

      if (serviceAccountKey) {
        // Initialize with service account key
        const serviceAccount = JSON.parse(serviceAccountKey);
        admin.initializeApp({
          credential: admin.credential.cert(serviceAccount),
          projectId: projectId
        });
      } else {
        // Initialize with default credentials (for GCP environments)
        admin.initializeApp({
          projectId: projectId
        });
      }
    }

    this.auth = admin.auth();
    this.firestoreClient = new FirestoreClient();
    
    console.log('✅ AuthMiddleware initialized');
  }

  /**
   * Verify Firebase ID token
   */
  verifyToken = async (req, res, next) => {
    try {
      const authHeader = req.headers.authorization;
      
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({
          success: false,
          error: 'No authorization token provided',
          code: 'AUTH_TOKEN_MISSING',
          timestamp: new Date().toISOString()
        });
      }

      const idToken = authHeader.split('Bearer ')[1];

      if (!idToken) {
        return res.status(401).json({
          success: false,
          error: 'Invalid authorization header format',
          code: 'AUTH_TOKEN_INVALID',
          timestamp: new Date().toISOString()
        });
      }

      // Verify the ID token
      const decodedToken = await this.auth.verifyIdToken(idToken);
      
      // Add user information to request
      req.user = {
        uid: decodedToken.uid,
        email: decodedToken.email,
        email_verified: decodedToken.email_verified,
        name: decodedToken.name,
        picture: decodedToken.picture,
        role: decodedToken.role || 'user',
        auth_time: decodedToken.auth_time,
        firebase: decodedToken
      };

      // Update user's last login time
      await this.updateUserLoginTime(req.user.uid, {
        ipAddress: req.ip,
        userAgent: req.get('User-Agent')
      });

      console.log(`✅ User authenticated: ${req.user.uid} (${req.user.email})`);
      next();

    } catch (error) {
      console.error('❌ Token verification failed:', error);
      
      let errorMessage = 'Invalid or expired token';
      let errorCode = 'AUTH_TOKEN_INVALID';

      if (error.code === 'auth/id-token-expired') {
        errorMessage = 'Token has expired';
        errorCode = 'AUTH_TOKEN_EXPIRED';
      } else if (error.code === 'auth/id-token-revoked') {
        errorMessage = 'Token has been revoked';
        errorCode = 'AUTH_TOKEN_REVOKED';
      } else if (error.code === 'auth/invalid-id-token') {
        errorMessage = 'Invalid token format';
        errorCode = 'AUTH_TOKEN_MALFORMED';
      }

      res.status(401).json({
        success: false,
        error: errorMessage,
        code: errorCode,
        timestamp: new Date().toISOString()
      });
    }
  };

  /**
   * Optional authentication - allows both authenticated and unauthenticated requests
   */
  optionalAuth = async (req, res, next) => {
    try {
      const authHeader = req.headers.authorization;
      
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        // No token provided, continue without user info
        req.user = null;
        return next();
      }

      const idToken = authHeader.split('Bearer ')[1];
      
      if (!idToken) {
        req.user = null;
        return next();
      }

      // Verify token if provided
      const decodedToken = await this.auth.verifyIdToken(idToken);
      
      req.user = {
        uid: decodedToken.uid,
        email: decodedToken.email,
        email_verified: decodedToken.email_verified,
        name: decodedToken.name,
        picture: decodedToken.picture,
        role: decodedToken.role || 'user',
        auth_time: decodedToken.auth_time,
        firebase: decodedToken
      };

      console.log(`✅ Optional auth - User identified: ${req.user.uid}`);

    } catch (error) {
      console.warn('⚠️ Optional auth - Token verification failed, continuing as unauthenticated');
      req.user = null;
    }

    next();
  };

  /**
   * Require specific role
   */
  requireRole = (requiredRole) => {
    return async (req, res, next) => {
      try {
        if (!req.user) {
          return res.status(401).json({
            success: false,
            error: 'Authentication required',
            code: 'AUTH_REQUIRED',
            timestamp: new Date().toISOString()
          });
        }

        // Get user profile to check role
        const userProfile = await this.firestoreClient.getUserProfile(req.user.uid);
        
        if (!userProfile) {
          return res.status(403).json({
            success: false,
            error: 'User profile not found',
            code: 'USER_PROFILE_MISSING',
            timestamp: new Date().toISOString()
          });
        }

        const userRole = userProfile.role || 'user';

        // Check role hierarchy
        if (!this.hasRole(userRole, requiredRole)) {
          return res.status(403).json({
            success: false,
            error: `Access denied. Required role: ${requiredRole}`,
            code: 'INSUFFICIENT_PERMISSIONS',
            userRole: userRole,
            requiredRole: requiredRole,
            timestamp: new Date().toISOString()
          });
        }

        // Add role to request user object
        req.user.role = userRole;
        
        console.log(`✅ Role check passed: ${req.user.uid} has role ${userRole}`);
        next();

      } catch (error) {
        console.error('❌ Role check failed:', error);
        res.status(500).json({
          success: false,
          error: 'Role verification failed',
          code: 'ROLE_CHECK_ERROR',
          timestamp: new Date().toISOString()
        });
      }
    };
  };

  /**
   * Check if user has access to specific case
   */
  requireCaseAccess = async (req, res, next) => {
    try {
      if (!req.user) {
        return res.status(401).json({
          success: false,
          error: 'Authentication required',
          code: 'AUTH_REQUIRED',
          timestamp: new Date().toISOString()
        });
      }

      const caseId = req.params.caseId || req.body.caseId || req.query.caseId;
      
      if (!caseId) {
        return res.status(400).json({
          success: false,
          error: 'Case ID is required',
          code: 'CASE_ID_MISSING',
          timestamp: new Date().toISOString()
        });
      }

      // Get case to check ownership
      const caseData = await this.firestoreClient.getCase(caseId);
      
      if (!caseData) {
        return res.status(404).json({
          success: false,
          error: 'Case not found',
          code: 'CASE_NOT_FOUND',
          timestamp: new Date().toISOString()
        });
      }

      // Check if user is the case owner or has admin role
      const userProfile = await this.firestoreClient.getUserProfile(req.user.uid);
      const userRole = userProfile?.role || 'user';

      if (caseData.createdBy !== req.user.uid && !this.hasRole(userRole, 'admin')) {
        return res.status(403).json({
          success: false,
          error: 'Access denied to this case',
          code: 'CASE_ACCESS_DENIED',
          timestamp: new Date().toISOString()
        });
      }

      // Add case data to request for future use
      req.case = caseData;
      
      console.log(`✅ Case access granted: ${req.user.uid} -> ${caseId}`);
      next();

    } catch (error) {
      console.error('❌ Case access check failed:', error);
      res.status(500).json({
        success: false,
        error: 'Case access verification failed',
        code: 'CASE_ACCESS_ERROR',
        timestamp: new Date().toISOString()
      });
    }
  };

  /**
   * Rate limiting middleware
   */
  rateLimit = (options = {}) => {
    const {
      windowMs = 15 * 60 * 1000, // 15 minutes
      maxRequests = 100,
      skipSuccessfulRequests = false,
      skipFailedRequests = false
    } = options;

    const requests = new Map();

    return (req, res, next) => {
      const identifier = req.user?.uid || req.ip;
      const now = Date.now();
      const windowStart = now - windowMs;

      // Clean old entries
      const userRequests = requests.get(identifier) || [];
      const recentRequests = userRequests.filter(timestamp => timestamp > windowStart);
      
      if (recentRequests.length >= maxRequests) {
        return res.status(429).json({
          success: false,
          error: 'Too many requests',
          code: 'RATE_LIMIT_EXCEEDED',
          retryAfter: Math.ceil((recentRequests[0] + windowMs - now) / 1000),
          timestamp: new Date().toISOString()
        });
      }

      // Track this request
      recentRequests.push(now);
      requests.set(identifier, recentRequests);

      // Clean up old entries periodically
      if (Math.random() < 0.01) { // 1% chance
        this.cleanupRateLimit(requests, windowStart);
      }

      next();
    };
  };

  /**
   * Validate API key (for service-to-service communication)
   */
  validateApiKey = (req, res, next) => {
    try {
      const apiKey = req.headers['x-api-key'] || req.query.apiKey;
      const expectedApiKey = process.env.INTERNAL_API_KEY;

      if (!expectedApiKey) {
        console.warn('⚠️ INTERNAL_API_KEY not set, skipping API key validation');
        return next();
      }

      if (!apiKey) {
        return res.status(401).json({
          success: false,
          error: 'API key required',
          code: 'API_KEY_MISSING',
          timestamp: new Date().toISOString()
        });
      }

      if (apiKey !== expectedApiKey) {
        return res.status(401).json({
          success: false,
          error: 'Invalid API key',
          code: 'API_KEY_INVALID',
          timestamp: new Date().toISOString()
        });
      }

      console.log('✅ API key validated');
      next();

    } catch (error) {
      console.error('❌ API key validation failed:', error);
      res.status(500).json({
        success: false,
        error: 'API key validation error',
        code: 'API_KEY_ERROR',
        timestamp: new Date().toISOString()
      });
    }
  };

  // ==================== UTILITY METHODS ====================

  /**
   * Check if user has specific role (with hierarchy)
   */
  hasRole(userRole, requiredRole) {
    const roleHierarchy = {
      'super_admin': 5,
      'admin': 4,
      'legal_professional': 3,
      'paralegal': 2,
      'user': 1,
      'guest': 0
    };

    const userLevel = roleHierarchy[userRole] || 0;
    const requiredLevel = roleHierarchy[requiredRole] || 0;

    return userLevel >= requiredLevel;
  }

  /**
   * Update user's last login time
   */
  async updateUserLoginTime(userId, metadata = {}) {
    try {
      await this.firestoreClient.saveUserProfile({
        uid: userId,
        lastLoginAt: new Date(),
        metadata: {
          ...metadata,
          lastLoginTimestamp: Date.now()
        }
      });

      // Log login activity
      await this.firestoreClient.logUserActivity(userId, 'user_login', metadata);

    } catch (error) {
      console.error('❌ Failed to update user login time:', error);
      // Don't throw error as this is not critical
    }
  }

  /**
   * Clean up old rate limit entries
   */
  cleanupRateLimit(requests, windowStart) {
    for (const [identifier, timestamps] of requests.entries()) {
      const recentRequests = timestamps.filter(timestamp => timestamp > windowStart);
      if (recentRequests.length === 0) {
        requests.delete(identifier);
      } else {
        requests.set(identifier, recentRequests);
      }
    }
  }

  /**
   * Create custom token for user
   */
  async createCustomToken(userId, additionalClaims = {}) {
    try {
      const customToken = await this.auth.createCustomToken(userId, additionalClaims);
      console.log(`✅ Custom token created for user: ${userId}`);
      return customToken;
    } catch (error) {
      console.error(`❌ Error creating custom token for ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Revoke refresh tokens for user
   */
  async revokeRefreshTokens(userId) {
    try {
      await this.auth.revokeRefreshTokens(userId);
      console.log(`✅ Refresh tokens revoked for user: ${userId}`);
      return true;
    } catch (error) {
      console.error(`❌ Error revoking tokens for ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Set custom user claims
   */
  async setCustomUserClaims(userId, customClaims) {
    try {
      await this.auth.setCustomUserClaims(userId, customClaims);
      console.log(`✅ Custom claims set for user: ${userId}`, customClaims);
      return true;
    } catch (error) {
      console.error(`❌ Error setting custom claims for ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Get user by email
   */
  async getUserByEmail(email) {
    try {
      const userRecord = await this.auth.getUserByEmail(email);
      return userRecord;
    } catch (error) {
      if (error.code === 'auth/user-not-found') {
        return null;
      }
      console.error(`❌ Error getting user by email ${email}:`, error);
      throw error;
    }
  }

  /**
   * Disable user account
   */
  async disableUser(userId) {
    try {
      await this.auth.updateUser(userId, { disabled: true });
      console.log(`✅ User account disabled: ${userId}`);
      return true;
    } catch (error) {
      console.error(`❌ Error disabling user ${userId}:`, error);
      throw error;
    }
  }
}

module.exports = AuthMiddleware;