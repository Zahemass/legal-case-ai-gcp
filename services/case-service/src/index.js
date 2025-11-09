// services/case-service/src/index.js
// Performance / Error / Trace agents - must be required before the rest of app code in some cases
try {
  // Trace & Error Reporting will auto-detect environment
  require('@google-cloud/trace-agent').start();
  require('@google-cloud/error-reporting')();
} catch (e) {
  console.warn('Optional Google tracing/error libs not started:', e.message);
}

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const caseRoutes = require('./routes/cases');
const authMiddleware = require('./middleware/auth');

// Import structured logging helper from auth file (or re-declare)
const { Logging } = require('@google-cloud/logging');
const logging = new Logging();
const logName = process.env.LOG_NAME || 'case-service-log';
const log = logging.log(logName);

function writeLog(severity, message, json = {}) {
  try {
    const entry = log.entry({ resource: { type: 'cloud_run_revision' } }, {
      severity,
      message,
      timestamp: new Date().toISOString(),
      ...json
    });
    log.write(entry).catch(err => console.error('Logging error:', err));
  } catch (e) {
    console[severity === 'ERROR' ? 'error' : 'log'](message, json);
  }
}


const app = express();
app.set('trust proxy', 1);
const PORT = process.env.PORT || 8080;

// Security and performance middleware
app.use(helmet({
  contentSecurityPolicy: false, // Disable CSP for API
}));

app.use(compression());

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || [
    'http://localhost:3000',
    'https://your-frontend-domain.com'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: {
    error: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// Body parsing middleware
app.use(express.json({ 
  limit: '10mb',
  type: 'application/json'
}));
app.use(express.urlencoded({ 
  extended: true,
  limit: '10mb'
}));

// Request logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  const method = req.method;
  const url = req.originalUrl;
  const ip = req.ip || req.connection.remoteAddress;
  
  console.log(`[${timestamp}] ${method} ${url} - IP: ${ip}`);
  
  // Log request completion
  const originalSend = res.send;
  res.send = function(data) {
    console.log(`[${timestamp}] ${method} ${url} - ${res.statusCode} - IP: ${ip}`);
    originalSend.call(this, data);
  };
  
  next();
});

// Health check endpoint (no auth required)
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'healthy',
    service: 'case-service',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV || 'development'
  });
});

// Readiness check
app.get('/ready', (req, res) => {
  // Add any readiness checks here (DB connections, etc.)
  res.status(200).json({ 
    status: 'ready',
    timestamp: new Date().toISOString()
  });
});

// Authentication middleware for all case routes
app.use('/cases', authMiddleware);

// API routes
app.use('/cases', caseRoutes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'Legal Case Management API',
    version: '1.0.0',
    status: 'running',
    endpoints: {
      health: '/health',
      ready: '/ready',
      cases: '/cases'
    }
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ 
    error: 'Route not found',
    path: req.originalUrl,
    method: req.method,
    timestamp: new Date().toISOString()
  });
});

// Global error handling middleware
app.use((error, req, res, next) => {
  console.error('Global Error Handler:', {
    error: error.message,
    stack: error.stack,
    url: req.originalUrl,
    method: req.method,
    timestamp: new Date().toISOString()
  });

  // Validation errors
  if (error.name === 'ValidationError') {
    return res.status(400).json({
      error: 'Validation failed',
      details: error.details || error.message
    });
  }

  // Firebase errors
  if (error.code && error.code.startsWith('auth/')) {
    return res.status(401).json({
      error: 'Authentication failed',
      code: error.code
    });
  }

  // Multer errors (if any file uploads)
  if (error.code === 'LIMIT_FILE_SIZE') {
    return res.status(400).json({
      error: 'File too large'
    });
  }

  // Default error response
  const statusCode = error.status || error.statusCode || 500;
  const message = process.env.NODE_ENV === 'production' 
    ? 'Internal server error' 
    : error.message;

  res.status(statusCode).json({
    error: message,
    timestamp: new Date().toISOString(),
    ...(process.env.NODE_ENV !== 'production' && { stack: error.stack })
  });
});

// Start server
const server = app.listen(PORT, '0.0.0.0', () => {
  writeLog('INFO', 'Case Service started', {
  port: PORT,
  environment: process.env.NODE_ENV || 'development',
  healthCheck: `/health`,
  timestamp: new Date().toISOString()
});

});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`\n🛑 Received ${signal}. Starting graceful shutdown...`);
  
  server.close((err) => {
    if (err) {
      console.error('❌ Error during server shutdown:', err);
      process.exit(1);
    }
    
    console.log('✅ Server closed successfully');
    console.log('👋 Case Service shutdown complete');
    process.exit(0);
  });

  // Force shutdown after 30 seconds
  setTimeout(() => {
    console.error('❌ Forced shutdown due to timeout');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

module.exports = app;