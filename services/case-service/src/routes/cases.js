// services/case-service/src/routes/cases.js
const express = require('express');
const { body, param, query } = require('express-validator');
const caseController = require('../controllers/caseController');

const router = express.Router();

// Validation middleware
const validateCaseCreation = [
  body('title')
    .notEmpty()
    .withMessage('Case title is required')
    .trim()
    .isLength({ min: 3, max: 200 })
    .withMessage('Case title must be between 3 and 200 characters'),
  
  body('description')
    .optional()
    .trim()
    .isLength({ max: 2000 })
    .withMessage('Description must not exceed 2000 characters'),
  
  body('type')
    .optional()
    .isIn(['civil', 'criminal', 'corporate', 'family', 'immigration', 'intellectual-property', 'labor', 'real-estate', 'tax', 'other'])
    .withMessage('Invalid case type'),
  
  body('priority')
    .optional()
    .isIn(['low', 'medium', 'high', 'urgent'])
    .withMessage('Invalid priority level'),
  
  body('clientName')
    .optional()
    .trim()
    .isLength({ max: 100 })
    .withMessage('Client name must not exceed 100 characters'),
  
  body('clientEmail')
    .optional()
    .isEmail()
    .withMessage('Invalid client email format'),
  
  body('dueDate')
    .optional()
    .isISO8601()
    .withMessage('Invalid due date format (use ISO 8601)')
];

const validateCaseUpdate = [
  body('title')
    .optional()
    .trim()
    .isLength({ min: 3, max: 200 })
    .withMessage('Case title must be between 3 and 200 characters'),
  
  body('description')
    .optional()
    .trim()
    .isLength({ max: 2000 })
    .withMessage('Description must not exceed 2000 characters'),
  
  body('status')
    .optional()
    .isIn(['active', 'pending', 'closed', 'archived', 'on-hold'])
    .withMessage('Invalid status'),
  
  body('type')
    .optional()
    .isIn(['civil', 'criminal', 'corporate', 'family', 'immigration', 'intellectual-property', 'labor', 'real-estate', 'tax', 'other'])
    .withMessage('Invalid case type'),
  
  body('priority')
    .optional()
    .isIn(['low', 'medium', 'high', 'urgent'])
    .withMessage('Invalid priority level'),
  
  body('clientName')
    .optional()
    .trim()
    .isLength({ max: 100 })
    .withMessage('Client name must not exceed 100 characters'),
  
  body('clientEmail')
    .optional()
    .isEmail()
    .withMessage('Invalid client email format'),
  
  body('dueDate')
    .optional()
    .isISO8601()
    .withMessage('Invalid due date format (use ISO 8601)')
];

const validateCaseId = [
  param('id')
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
  
  query('status')
    .optional()
    .isIn(['active', 'pending', 'closed', 'archived', 'on-hold'])
    .withMessage('Invalid status filter'),
  
  query('type')
    .optional()
    .isIn(['civil', 'criminal', 'corporate', 'family', 'immigration', 'intellectual-property', 'labor', 'real-estate', 'tax', 'other'])
    .withMessage('Invalid type filter'),
  
  query('priority')
    .optional()
    .isIn(['low', 'medium', 'high', 'urgent'])
    .withMessage('Invalid priority filter'),
  
  query('sortBy')
    .optional()
    .isIn(['createdAt', 'updatedAt', 'title', 'dueDate', 'priority'])
    .withMessage('Invalid sort field'),
  
  query('order')
    .optional()
    .isIn(['asc', 'desc'])
    .withMessage('Order must be either "asc" or "desc"')
];

// Routes

/**
 * GET /cases
 * Get all cases for the authenticated user
 */
router.get('/', validateQueryParams, caseController.getCases);

/**
 * GET /cases/stats
 * Get case statistics for the authenticated user
 */
router.get('/stats', caseController.getCaseStatistics);

/**
 * GET /cases/:id
 * Get a specific case by ID
 */
router.get('/:id', validateCaseId, caseController.getCaseById);

/**
 * POST /cases
 * Create a new case
 */
router.post('/', validateCaseCreation, caseController.createCase);

/**
 * PUT /cases/:id
 * Update an existing case
 */
router.put('/:id', validateCaseId, validateCaseUpdate, caseController.updateCase);

/**
 * DELETE /cases/:id
 * Delete a case (soft delete)
 */
router.delete('/:id', validateCaseId, caseController.deleteCase);

/**
 * POST /cases/:id/analyze
 * Trigger AI analysis for a case
 */
router.post('/:id/analyze', validateCaseId, caseController.runCaseAnalysis);

/**
 * GET /cases/:id/stats
 * Get detailed statistics for a specific case
 */
router.get('/:id/stats', validateCaseId, caseController.getCaseStats);

/**
 * POST /cases/:id/duplicate
 * Create a duplicate of an existing case
 */
router.post('/:id/duplicate', validateCaseId, caseController.duplicateCase);

/**
 * POST /cases/:id/archive
 * Archive a case
 */
router.post('/:id/archive', validateCaseId, caseController.archiveCase);

/**
 * POST /cases/:id/restore
 * Restore an archived case
 */
router.post('/:id/restore', validateCaseId, caseController.restoreCase);

/**
 * GET /cases/:id/timeline
 * Get case activity timeline
 */
router.get('/:id/timeline', validateCaseId, caseController.getCaseTimeline);

/**
 * POST /cases/:id/notes
 * Add a note to a case
 */
router.post('/:id/notes', [
  ...validateCaseId,
  body('content')
    .notEmpty()
    .withMessage('Note content is required')
    .trim()
    .isLength({ min: 1, max: 1000 })
    .withMessage('Note content must be between 1 and 1000 characters'),
  body('type')
    .optional()
    .isIn(['general', 'important', 'reminder', 'meeting', 'call', 'email'])
    .withMessage('Invalid note type')
], caseController.addCaseNote);

/**
 * GET /cases/:id/notes
 * Get all notes for a case
 */
router.get('/:id/notes', validateCaseId, caseController.getCaseNotes);

module.exports = router;