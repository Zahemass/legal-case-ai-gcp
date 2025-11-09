const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');
require('dotenv').config();

const emailSender = require('./emailSender');
const { PubSub } = require('@google-cloud/pubsub');
const { Firestore } = require('@google-cloud/firestore');

const app = express();
const PORT = process.env.PORT || 8080;

// Initialize services
const pubsub = new PubSub();
const firestore = new Firestore();

// Configuration
const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT;
const SUBSCRIPTION_NAME = 'email-notification-subscription';
const MAX_WORKERS = parseInt(process.env.MAX_WORKERS) || 5;

// Security and performance middleware
app.use(helmet({
  contentSecurityPolicy: false,
}));

app.use(compression());

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || [
    'http://localhost:3000',
    'https://your-frontend-domain.com'
  ],
  credentials: true,
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: {
    error: 'Too many email requests from this IP, please try again later.'
  },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

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
    const responseTime = Date.now() - req.startTime;
    console.log(`[${timestamp}] ${method} ${url} - ${res.statusCode} - ${responseTime}ms - IP: ${ip}`);
    originalSend.call(this, data);
  };
  
  req.startTime = Date.now();
  next();
});

// Global variables for tracking
const activeJobs = new Set();
const emailStats = {
  sent: 0,
  failed: 0,
  startTime: Date.now()
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'healthy',
    service: 'email-service',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.NODE_ENV || 'development',
    activeJobs: activeJobs.size,
    emailStats: {
      ...emailStats,
      uptime: Date.now() - emailStats.startTime
    }
  });
});

// Readiness check
app.get('/ready', (req, res) => {
  try {
    // Test email service configuration
    if (!emailSender.isConfigured()) {
      return res.status(503).json({ 
        status: 'not_ready',
        error: 'Email service not properly configured',
        timestamp: new Date().toISOString()
      });
    }
    
    res.status(200).json({ 
      status: 'ready',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Readiness check failed:', error);
    res.status(503).json({
      status: 'not_ready',
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

// Email sending endpoint
app.post('/send', [
  body('to').isEmail().withMessage('Valid email address is required'),
  body('subject').notEmpty().trim().withMessage('Subject is required'),
  body('template').notEmpty().withMessage('Template name is required'),
  body('data').optional().isObject().withMessage('Template data must be an object')
], async (req, res) => {
  try {
    // Check validation errors
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        error: 'Validation failed',
        details: errors.array(),
        timestamp: new Date().toISOString()
      });
    }

    const { to, subject, template, data = {}, priority = 'normal' } = req.body;
    
    console.log(`📧 Processing email request: ${template} to ${to}`);
    
    // Send email
    const result = await emailSender.sendEmail({
      to,
      subject,
      template,
      data,
      priority
    });

    if (result.success) {
      emailStats.sent++;
      console.log(`✅ Email sent successfully to ${to}`);
      
      res.json({
        success: true,
        message: 'Email sent successfully',
        messageId: result.messageId,
        timestamp: new Date().toISOString()
      });
    } else {
      emailStats.failed++;
      console.error(`❌ Email sending failed: ${result.error}`);
      
      res.status(500).json({
        success: false,
        error: result.error,
        timestamp: new Date().toISOString()
      });
    }

  } catch (error) {
    emailStats.failed++;
    console.error('❌ Email endpoint error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to send email',
      timestamp: new Date().toISOString()
    });
  }
});

// Bulk email endpoint
app.post('/send-bulk', [
  body('emails').isArray({ min: 1, max: 50 }).withMessage('Emails array required (max 50)'),
  body('emails.*.to').isEmail().withMessage('Valid email address required for each recipient'),
  body('emails.*.subject').notEmpty().withMessage('Subject required for each email'),
  body('emails.*.template').notEmpty().withMessage('Template required for each email')
], async (req, res) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        error: 'Validation failed',
        details: errors.array(),
        timestamp: new Date().toISOString()
      });
    }

    const { emails } = req.body;
    
    console.log(`📧 Processing bulk email request: ${emails.length} emails`);
    
    const results = await emailSender.sendBulkEmail(emails);
    
    const successCount = results.filter(r => r.success).length;
    const failureCount = results.filter(r => !r.success).length;
    
    emailStats.sent += successCount;
    emailStats.failed += failureCount;
    
    console.log(`✅ Bulk email completed: ${successCount} sent, ${failureCount} failed`);
    
    res.json({
      success: successCount > 0,
      message: `Bulk email completed: ${successCount} sent, ${failureCount} failed`,
      results,
      summary: {
        total: emails.length,
        sent: successCount,
        failed: failureCount
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ Bulk email error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to send bulk emails',
      timestamp: new Date().toISOString()
    });
  }
});

// Email statistics endpoint
app.get('/stats', (req, res) => {
  const uptime = Date.now() - emailStats.startTime;
  const uptimeHours = Math.floor(uptime / (1000 * 60 * 60));
  
  res.json({
    ...emailStats,
    uptime: uptime,
    uptimeHours: uptimeHours,
    successRate: emailStats.sent + emailStats.failed > 0 
      ? ((emailStats.sent / (emailStats.sent + emailStats.failed)) * 100).toFixed(2) + '%'
      : '0%',
    activeJobs: activeJobs.size,
    timestamp: new Date().toISOString()
  });
});

// Test email endpoint
app.post('/test', [
  body('to').isEmail().withMessage('Valid email address is required')
], async (req, res) => {
  try {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        success: false,
        error: 'Validation failed',
        details: errors.array()
      });
    }

    const { to } = req.body;
    
    const result = await emailSender.sendEmail({
      to,
      subject: 'Legal Case AI - Email Service Test',
      template: 'test',
      data: {
        testTime: new Date().toISOString(),
        serviceName: 'Legal Case AI Email Service'
      }
    });

    res.json({
      success: result.success,
      message: result.success ? 'Test email sent successfully' : 'Test email failed',
      error: result.error,
      messageId: result.messageId,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ Test email error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to send test email',
      timestamp: new Date().toISOString()
    });
  }
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({
    service: 'Legal Case AI Email Service',
    version: '1.0.0',
    status: 'running',
    endpoints: {
      health: '/health',
      ready: '/ready',
      send: 'POST /send',
      sendBulk: 'POST /send-bulk',
      test: 'POST /test',
      stats: '/stats'
    },
    features: [
      'Email notifications',
      'Template-based emails',
      'Bulk email sending',
      'Multiple email providers',
      'HTML and text email support'
    ],
    supportedTemplates: [
      'analysis-complete',
      'case-created',
      'document-uploaded',
      'report-ready',
      'test'
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
  console.error('Global Error Handler:', {
    error: error.message,
    stack: error.stack,
    url: req.originalUrl,
    method: req.method,
    timestamp: new Date().toISOString()
  });

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

// Pub/Sub message processing
async function processEmailMessage(message) {
  const jobId = `email_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  try {
    activeJobs.add(jobId);
    
    const data = JSON.parse(message.data.decode('utf-8'));
    console.log(`📧 Processing email message: ${jobId}`, data);
    
    const { to, subject, template, templateData, priority = 'normal' } = data;
    
    if (!to || !subject || !template) {
      throw new Error('Missing required email fields: to, subject, template');
    }
    
    const result = await emailSender.sendEmail({
      to,
      subject,
      template,
      data: templateData || {},
      priority
    });

    if (result.success) {
      emailStats.sent++;
      console.log(`✅ Email sent via Pub/Sub: ${jobId} to ${to}`);
      message.ack();
    } else {
      emailStats.failed++;
      console.error(`❌ Email failed via Pub/Sub: ${jobId} - ${result.error}`);
      message.nack();
    }

  } catch (error) {
    emailStats.failed++;
    console.error(`❌ Email processing error: ${jobId}`, error);
    message.nack();
  } finally {
    activeJobs.delete(jobId);
  }
}

// Start Pub/Sub subscriber
function startSubscriber() {
  if (!PROJECT_ID) {
    console.warn('⚠️ GOOGLE_CLOUD_PROJECT not set, Pub/Sub subscriber disabled');
    return;
  }

  const subscriber = pubsub.subscription(`projects/${PROJECT_ID}/subscriptions/${SUBSCRIPTION_NAME}`);
  
  // Configure flow control
  subscriber.setOptions({
    flowControlSettings: {
      maxMessages: MAX_WORKERS,
      allowExcessMessages: false
    }
  });

  console.log(`🔄 Starting Pub/Sub subscriber: ${SUBSCRIPTION_NAME}`);
  
  subscriber.on('message', processEmailMessage);
  
  subscriber.on('error', error => {
    console.error('❌ Pub/Sub subscriber error:', error);
  });

  console.log('✅ Pub/Sub subscriber started');
}

// Start server
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`
📧 Email Service Started Successfully!
📅 Time: ${new Date().toISOString()}
🌐 Port: ${PORT}
🔧 Environment: ${process.env.NODE_ENV || 'development'}
📋 Health Check: http://localhost:${PORT}/health
✉️ Email Provider: ${emailSender.getProviderName()}
  `);
  
  // Start Pub/Sub subscriber
  startSubscriber();
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
  console.log(`\n🛑 Received ${signal}. Starting graceful shutdown...`);
  
  server.close((err) => {
    if (err) {
      console.error('❌ Error during server shutdown:', err);
      process.exit(1);
    }
    
    // Wait for active jobs to complete
    const checkActiveJobs = () => {
      if (activeJobs.size === 0) {
        console.log('✅ All email jobs completed');
        console.log('👋 Email Service shutdown complete');
        process.exit(0);
      } else {
        console.log(`⏳ Waiting for ${activeJobs.size} active email jobs...`);
        setTimeout(checkActiveJobs, 2000);
      }
    };
    
    checkActiveJobs();
    
    // Force shutdown after 30 seconds
    setTimeout(() => {
      console.error('❌ Forced shutdown due to timeout');
      process.exit(1);
    }, 30000);
  });
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