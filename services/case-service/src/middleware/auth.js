// services/case-service/src/middleware/auth.js
const admin = require('firebase-admin');
const { Logging } = require('@google-cloud/logging');

// Initialize Google Cloud Logging client for structured logs
const logging = new Logging();
const logName = process.env.LOG_NAME || 'case-service-log';
const log = logging.log(logName);

// Simple structured logger helper (INFO / ERROR)
function writeLog(severity, message, json = {}) {
  try {
    const entry = log.entry({ resource: { type: 'cloud_run_revision' } }, {
      severity: severity,
      message,
      timestamp: new Date().toISOString(),
      ...json
    });
    log.write(entry).catch(err => console.error('Logging error:', err));
  } catch (e) {
    // fallback to console
    console[severity === 'ERROR' ? 'error' : 'log'](message, json);
  }
}

// Initialize Firebase Admin SDK (use explicit PROJECT_ID env if available)
if (!admin.apps.length) {
  try {
    const projectId = process.env.PROJECT_ID || process.env.GOOGLE_CLOUD_PROJECT;
    writeLog('INFO', 'Initializing Firebase Admin SDK', { projectId });
    admin.initializeApp({
      credential: admin.credential.applicationDefault(),
      projectId
    });
    writeLog('INFO', 'Firebase Admin SDK initialized successfully', { projectId });
  } catch (error) {
    writeLog('ERROR', 'Failed to initialize Firebase Admin SDK', { error: error.message });
    throw error;
  }
}


/**
 * Authentication middleware for Firebase JWT tokens
 */
const authenticateToken = async (req, res, next) => {
  try {
    // Extract authorization header
    const authHeader = req.headers.authorization;
    
    if (!authHeader) {
      return res.status(401).json({ 
        error: 'Authorization header is required',
        code: 'MISSING_AUTH_HEADER'
      });
    }

    // Check if header starts with 'Bearer '
    if (!authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ 
        error: 'Authorization header must start with "Bearer "',
        code: 'INVALID_AUTH_FORMAT'
      });
    }

    // Extract token
    const token = authHeader.split(' ')[1];
    
    if (!token) {
      return res.status(401).json({ 
        error: 'No token provided in authorization header',
        code: 'MISSING_TOKEN'
      });
    }

    // Verify token with Firebase Admin
    console.log('🔍 Verifying token using project:', process.env.GOOGLE_CLOUD_PROJECT);

    const decodedToken = await admin.auth().verifyIdToken(token, true);
    console.log('✅ Token verified:', decodedToken);

    
    // Add user info to request object
    req.user = {
      uid: decodedToken.uid,
      email: decodedToken.email,
      email_verified: decodedToken.email_verified,
      name: decodedToken.name,
      picture: decodedToken.picture,
      iss: decodedToken.iss,
      aud: decodedToken.aud,
      auth_time: decodedToken.auth_time,
      exp: decodedToken.exp,
      iat: decodedToken.iat,
      firebase: decodedToken.firebase
    };

    // Log successful authentication (without sensitive data)
    console.log(`✅ User authenticated: ${decodedToken.uid} (${decodedToken.email})`);
    
    next();
    
  } catch (error) {
    console.error('❌ Authentication error:', error);
    
    // Handle specific Firebase Auth errors
    let errorResponse = {
      error: 'Authentication failed',
      code: 'AUTH_FAILED',
      timestamp: new Date().toISOString()
    };

    switch (error.code) {
      case 'auth/id-token-expired':
        errorResponse.error = 'Token has expired';
        errorResponse.code = 'TOKEN_EXPIRED';
        break;
        
      case 'auth/id-token-revoked':
        errorResponse.error = 'Token has been revoked';
        errorResponse.code = 'TOKEN_REVOKED';
        break;
        
      case 'auth/invalid-id-token':
        errorResponse.error = 'Invalid token format';
        errorResponse.code = 'INVALID_TOKEN';
        break;
        
      case 'auth/project-not-found':
        errorResponse.error = 'Firebase project not found';
        errorResponse.code = 'PROJECT_NOT_FOUND';
        break;
        
      case 'auth/insufficient-permission':
        errorResponse.error = 'Insufficient permissions';
        errorResponse.code = 'INSUFFICIENT_PERMISSION';
        break;
        
      default:
        if (error.message.includes('Token used too early')) {
          errorResponse.error = 'Token used before valid time';
          errorResponse.code = 'TOKEN_TOO_EARLY';
        } else if (error.message.includes('Firebase ID token has no')) {
          errorResponse.error = 'Token missing required claims';
          errorResponse.code = 'MISSING_CLAIMS';
        }
        break;
    }

    return res.status(401).json(errorResponse);
  }
};

/**
 * Optional authentication middleware (allows requests without auth)
 */
const optionalAuth = async (req, res, next) => {
  const authHeader = req.headers.authorization;
  
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    // No auth provided, continue without user
    req.user = null;
    return next();
  }

  // Auth provided, validate it
  return authenticateToken(req, res, next);
};

/**
 * Role-based authorization middleware
 */
const requireRole = (allowedRoles) => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ 
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    const userRoles = req.user.firebase?.sign_in_attributes?.custom_claims?.roles || [];
    const hasRole = allowedRoles.some(role => userRoles.includes(role));

    if (!hasRole) {
      return res.status(403).json({ 
        error: 'Insufficient permissions',
        code: 'INSUFFICIENT_ROLE',
        requiredRoles: allowedRoles,
        userRoles
      });
    }

    next();
  };
};

/**
 * Check if user owns resource
 */
const requireOwnership = (resourceField = 'createdBy') => {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ 
        error: 'Authentication required',
        code: 'AUTH_REQUIRED'
      });
    }

    // This will be used in controllers to check ownership
    // The actual ownership check happens in the controller
    req.ownershipField = resourceField;
    next();
  };
};

module.exports = authenticateToken;
module.exports.optionalAuth = optionalAuth;
module.exports.requireRole = requireRole;
module.exports.requireOwnership = requireOwnership;