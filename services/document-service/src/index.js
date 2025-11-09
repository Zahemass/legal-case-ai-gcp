// services/document-service/src/index.js
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const multer = require('multer');
require('dotenv').config();

const documentRoutes = require('./routes/documents');

const app = express();
app.set('trust proxy', 1);
const PORT = process.env.PORT || 8080;

// Security and performance middleware
app.use(helmet({
  contentSecurityPolicy: false,
  crossOriginResourcePolicy: { policy: "cross-origin" }
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

// Rate limiting - more lenient for file uploads
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 50, // limit each IP to 50 requests per windowMs
  skipSuccessfulRequests: true,
  message: {
    error: 'Too many requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// Configure multer for file uploads
const storage = multer.memoryStorage();
const upload = multer({ 
  storage,
  limits: { 
    fileSize: 100 * 1024 * 1024, // 100MB limit
    files: 20 // max 20 files per request
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = [
      'application/pdf',
      'text/plain',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-powerpoint',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/webp',
      'application/rtf',
      'text/csv'
    ];
    
    if (allowedTypes.includes(file.mimetype)) {
      cb(null, true);
    } else {
      cb(new Error(`Invalid file type: ${file.mimetype}. Allowed types: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, RTF, CSV, JPG, PNG, GIF, WEBP`));
    }
  }
});

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
  const timestamp = new Date().toISOString();
  const method = req.method;
  const url = req.originalUrl;
  const ip = req.ip || req.connection.remoteAddress;
  const userAgent = req.get('User-Agent') || 'Unknown';
  
  console.log(`[${timestamp}] ${method} ${url} - IP: ${ip} - UA: ${userAgent.substring(0, 50)}`);
  
  // Log request completion
  const originalSend = res.send;
  res.send = function(data) {
    const responseTime = Date.now() - req.startTime;
    console.log(`[${timestamp}] ${method} ${url} - ${res.statusCode} - ${responseTime}ms - IP: ${ip}`);
    originalSend.call(this, data);
  };
  
  req.startTime = Date.now();
  next();
});

// Make upload middleware available to routes
app.locals.upload = upload;

// Health check endpoint (no auth required)
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'healthy',
    service: 'document-service',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV || 'development',
    limits: {
      maxFileSize: '100MB',
      maxFiles: 20,
      allowedTypes: ['PDF', 'DOC', 'DOCX', 'XLS', 'XLSX', 'PPT', 'PPTX', 'TXT', 'RTF', 'CSV', 'Images']
    }
  });
});

// Readiness check
app.get('/ready', (req, res) => {
  // Add any readiness checks here (storage connections, etc.)
  res.status(200).json({ 
    status: 'ready',
    timestamp: new Date().toISOString()
  });
});

// Routes
app.use('/documents', documentRoutes);

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'Legal Document Management API',
    version: '1.0.0',
    status: 'running',
    endpoints: {
      health: '/health',
      ready: '/ready',
      documents: '/documents'
    },
    features: [
      'Document Upload',
      'File Preview',
      'Text Extraction',
      'Document Analysis',
      'Batch Operations'
    ]
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
  console.log('Global Error Handler:', {
    error: error.message,
    stack: error.stack,
    url: req.originalUrl,
    method: req.method,
    timestamp: new Date().toISOString()
  });

  // Multer errors
  if (error instanceof multer.MulterError) {
    switch (error.code) {
      case 'LIMIT_FILE_SIZE':
        return res.status(400).json({
          error: 'File too large',
          details: 'Maximum file size is 100MB',
          code: 'FILE_TOO_LARGE'
        });
      case 'LIMIT_FILE_COUNT':
        return res.status(400).json({
          error: 'Too many files',
          details: 'Maximum 20 files per request',
          code: 'TOO_MANY_FILES'
        });
      case 'LIMIT_UNEXPECTED_FILE':
        return res.status(400).json({
          error: 'Unexpected file field',
          code: 'UNEXPECTED_FILE'
        });
      default:
        return res.status(400).json({
          error: 'File upload error',
          details: error.message,
          code: error.code
        });
    }
  }

  // File type errors
  if (error.message.includes('Invalid file type')) {
    return res.status(400).json({
      error: 'Invalid file type',
      details: error.message,
      code: 'INVALID_FILE_TYPE'
    });
  }

  // Validation errors
  if (error.name === 'ValidationError') {
    return res.status(400).json({
      error: 'Validation failed',
      details: error.details || error.message,
      code: 'VALIDATION_ERROR'
    });
  }

  // Firebase errors
  if (error.code && error.code.startsWith('auth/')) {
    return res.status(401).json({
      error: 'Authentication failed',
      code: error.code
    });
  }

  // Storage errors
  if (error.code && error.code.includes('storage')) {
    return res.status(500).json({
      error: 'Storage operation failed',
      details: process.env.NODE_ENV === 'production' ? 'Internal storage error' : error.message,
      code: 'STORAGE_ERROR'
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
  console.log(`
📄 Document Service Started Successfully!
📅 Time: ${new Date().toISOString()}
🌐 Port: ${PORT}
🔧 Environment: ${process.env.NODE_ENV || 'development'}
💾 Storage Bucket: ${process.env.STORAGE_BUCKET || 'Not configured'}
📋 Health Check: http://localhost:${PORT}/health
  `);
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`\n🛑 Received ${signal}. Starting graceful shutdown...`);
  
  server.close((err) => {
    if (err) {
      console.log('❌ Error during server shutdown:', err);
      process.exit(1);
    }
    
    console.log('✅ Server closed successfully');
    console.log('👋 Document Service shutdown complete');
    process.exit(0);
  });

  // Force shutdown after 30 seconds
  setTimeout(() => {
    console.log('❌ Forced shutdown due to timeout');
    process.exit(1);
  }, 30000);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  console.log('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.log('Uncaught Exception:', error);
  process.exit(1);
});

module.exports = app;