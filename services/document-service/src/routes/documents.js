// services/document-service/src/routes/documents.js
const express = require('express');
const { body, param, query } = require('express-validator');
const uploadController = require('../controllers/uploadController');
const previewController = require('../controllers/previewController');

// Import auth middleware from shared folder
// ✅ Use AuthMiddleware class properly
const AuthMiddleware = require('../../shared/nodejs/auth-middleware');
const auth = new AuthMiddleware();

const router = express.Router();

// Apply authentication to all routes
// ✅ Apply token verification middleware
router.use(auth.verifyToken);


// Validation middleware
const validateDocumentId = [
  param('id')
    .notEmpty()
    .withMessage('Document ID is required')
    .isString()
    .withMessage('Document ID must be a string')
];

const validateCaseId = [
  body('caseId')
    .notEmpty()
    .withMessage('Case ID is required')
    .isString()
    .withMessage('Case ID must be a string')
];

const validateQueryParams = [
  query('limit')
    .optional()
    .isInt({ min: 1, max: 100 })
    .withMessage('Limit must be between 1 and 100'),
  
  query('offset')
    .optional()
    .isInt({ min: 0 })
    .withMessage('Offset must be a non-negative integer'),
  
  query('sortBy')
    .optional()
    .isIn(['uploadedAt', 'filename', 'size', 'status'])
    .withMessage('Invalid sort field'),
  
  query('order')
    .optional()
    .isIn(['asc', 'desc'])
    .withMessage('Order must be either "asc" or "desc"'),
  
  query('status')
    .optional()
    .isIn(['uploaded', 'processing', 'extracted', 'analyzed', 'error', 'deleted'])
    .withMessage('Invalid status filter'),
  
  query('type')
    .optional()
    .isString()
    .withMessage('Type must be a string')
];

const validateBatchOperation = [
  body('documentIds')
    .isArray({ min: 1 })
    .withMessage('Document IDs array is required with at least one ID'),
  
  body('documentIds.*')
    .isString()
    .withMessage('Each document ID must be a string')
];

// Routes

/**
 * GET /documents
 * Get all documents for the authenticated user
 */
router.get('/', validateQueryParams, uploadController.getDocuments);

/**
 * GET /documents/stats
 * Get document statistics for the authenticated user
 */
router.get('/stats', uploadController.getDocumentStatistics);

/**
 * GET /documents/:id
 * Get a specific document by ID
 */
router.get('/:id', validateDocumentId, uploadController.getDocumentById);

/**
 * POST /documents/upload
 * Upload one or more documents
 */
router.post('/upload', [
  (req, res, next) => {
    req.app.locals.upload.array('files', 20)(req, res, next);
  },
  validateCaseId
], uploadController.uploadDocuments);

/**
 * DELETE /documents/:id
 * Delete a document (soft delete)
 */
router.delete('/:id', validateDocumentId, uploadController.deleteDocument);

/**
 * GET /documents/:id/preview
 * Get document preview/content
 */
router.get('/:id/preview', validateDocumentId, previewController.getDocumentPreview);

/**
 * GET /documents/:id/download
 * Download original document
 */
router.get('/:id/download', validateDocumentId, uploadController.downloadDocument);

/**
 * POST /documents/:id/analyze
 * Trigger AI analysis for a document
 */
router.post('/:id/analyze', validateDocumentId, uploadController.analyzeDocument);

/**
 * GET /documents/:id/analysis
 * Get document analysis results
 */
router.get('/:id/analysis', validateDocumentId, uploadController.getDocumentAnalysis);

/**
 * POST /documents/batch/analyze
 * Batch analyze multiple documents
 */
router.post('/batch/analyze', validateBatchOperation, uploadController.batchAnalyzeDocuments);

/**
 * POST /documents/batch/delete
 * Batch delete multiple documents
 */
router.post('/batch/delete', validateBatchOperation, uploadController.batchDeleteDocuments);

/**
 * PUT /documents/:id/metadata
 * Update document metadata
 */
router.put('/:id/metadata', [
  ...validateDocumentId,
  body('filename')
    .optional()
    .isString()
    .isLength({ min: 1, max: 255 })
    .withMessage('Filename must be between 1 and 255 characters'),
  
  body('description')
    .optional()
    .isString()
    .isLength({ max: 1000 })
    .withMessage('Description must not exceed 1000 characters'),
  
  body('tags')
    .optional()
    .isArray()
    .withMessage('Tags must be an array'),
  
  body('tags.*')
    .optional()
    .isString()
    .withMessage('Each tag must be a string')
], uploadController.updateDocumentMetadata);

/**
 * POST /documents/:id/extract
 * Trigger text extraction for a document
 */
router.post('/:id/extract', validateDocumentId, uploadController.extractDocument);

/**
 * GET /documents/:id/extraction-status
 * Get document extraction status
 */
router.get('/:id/extraction-status', validateDocumentId, uploadController.getExtractionStatus);

module.exports = router;