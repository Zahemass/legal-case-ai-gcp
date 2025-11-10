const { Firestore } = require('@google-cloud/firestore');
const { PubSub } = require('@google-cloud/pubsub');
const { validationResult } = require('express-validator');
const { Logging } = require('@google-cloud/logging');

// init clients
const firestore = new Firestore();
const pubsub = new PubSub();

// Logging
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

// Collections (constants)
const CASES_COLLECTION = 'cases';
const DOCUMENTS_COLLECTION = 'documents';
const CASE_NOTES_COLLECTION = 'case_notes';
const CASE_ACTIVITIES_COLLECTION = 'case_activities';

// Pub/Sub topic name from env
const CASE_ANALYSIS_TOPIC = process.env.CASE_ANALYSIS_TOPIC || 'analysis-requests';


/**
 * Handle validation errors
 */
const handleValidationErrors = (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      error: 'Validation failed',
      details: errors.array()
    });
  }
  return null;
};

/**
 * Log case activity
 */
const logCaseActivity = async (caseId, userId, action, details = {}) => {
  try {
    await firestore.collection(CASE_ACTIVITIES_COLLECTION).add({
      caseId,
      userId,
      action,
      details,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    writeLog('ERROR', 'Error logging case activity:', { error: error.message });
  }
};

/**
 * GET /cases
 * Get all cases for the authenticated user
 */
exports.getCases = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { 
      status, 
      type, 
      priority, 
      limit = 20, 
      offset = 0, 
      sortBy = 'createdAt', 
      order = 'desc',
      search 
    } = req.query;
    
    let query = firestore.collection(CASES_COLLECTION);
    
    // Filter only the logged-in user's cases
    query = query.where('createdBy', '==', req.user.uid);
    
    // Optional filters
    if (status) query = query.where('status', '==', status);
    if (type) query = query.where('type', '==', type);
    if (priority) query = query.where('priority', '==', priority);

    // ✅ FIXED: Firestore-safe filter (exclude deleted)
    if (!status) {
      query = query.where('status', 'in', ['active', 'pending', 'closed', 'archived', 'on-hold']);
    }

    // ✅ FIXED: Safe sorting (must order by field used in filter first)
    query = query.orderBy('status').orderBy(sortBy, order);
    
    // Pagination
    query = query.limit(parseInt(limit)).offset(parseInt(offset));
    
    const snapshot = await query.get();
    const cases = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));

    // Client-side search
    if (search) {
      const searchTerm = search.toLowerCase();
      cases = cases.filter(c => 
        c.title?.toLowerCase().includes(searchTerm) ||
        c.description?.toLowerCase().includes(searchTerm) ||
        c.clientName?.toLowerCase().includes(searchTerm)
      );
    }

    // Document counts (optional)
    // ✅ Fix: Use existing Firestore field if available, fallback to live count
for (let c of cases) {
  // Prefer Firestore-stored field first
  if (typeof c.documentCount === 'number' && c.documentCount >= 0) {
    continue; // skip recalculating if already in Firestore
  }

  const docsSnapshot = await firestore
    .collection(DOCUMENTS_COLLECTION)
    .where('caseId', '==', c.id)
    .where('status', 'in', ['active', 'processed', 'pending'])
    .get();

  c.documentCount = docsSnapshot.size || 0;
}


    // ✅ FIXED: Count query without unsupported filters
    const totalSnapshot = await firestore
      .collection(CASES_COLLECTION)
      .where('createdBy', '==', req.user.uid)
      .where('status', 'in', ['active', 'pending', 'closed', 'archived', 'on-hold'])
      .get();
    
    const totalCount = totalSnapshot.size;

    res.json({
      success: true,
      data: {
        cases,
        pagination: {
          limit: parseInt(limit),
          offset: parseInt(offset),
          total: totalCount,
          hasMore: totalCount > parseInt(offset) + cases.length
        }
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('🔥 Firestore query failed:', error);
    writeLog('ERROR', 'Error getting cases:', { error: error.message, stack: error.stack });
    res.status(500).json({ 
      success: false,
      error: 'Failed to fetch cases',
      details: error.message, // Optional: helps confirm exact Firestore error
      timestamp: new Date().toISOString()
    });
  }
};


/**
 * GET /cases/:id
 * Get a specific case by ID
 */
exports.getCaseById = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const doc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }

    const caseData = doc.data();
    
    // Check if user has access to this case
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Get document count
    const docsSnapshot = await firestore
      .collection(DOCUMENTS_COLLECTION)
      .where('caseId', '==', id)
      .where('status', '!=', 'deleted')
      .get();

    const enrichedCaseData = {
      id: doc.id,
      ...caseData,
      documentCount: docsSnapshot.size
    };

    res.json({
      success: true,
      data: enrichedCaseData,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to get case:', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to fetch case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /cases
 * Create a new case
 */
exports.createCase = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { 
      title, 
      description, 
      type, 
      priority, 
      clientName, 
      clientEmail, 
      dueDate 
    } = req.body;

    const now = new Date().toISOString();
    
    const caseData = {
      title: title.trim(),
      description: description?.trim() || '',
      type: type || 'other',
      priority: priority || 'medium',
      status: 'active',
      clientName: clientName?.trim() || '',
      clientEmail: clientEmail?.trim() || '',
      dueDate: dueDate || null,
      createdBy: req.user.uid,
      createdAt: now,
      updatedAt: now,
      documentCount: 0,
      analysisCount: 0,
      version: 1
    };

    const docRef = await firestore.collection(CASES_COLLECTION).add(caseData);
    const newCase = { id: docRef.id, ...caseData };

    // Log activity
    await logCaseActivity(docRef.id, req.user.uid, 'case_created', {
      title: caseData.title,
      type: caseData.type
    });

    writeLog('INFO', 'Case created', { caseId: docRef.id, userId: req.user.uid, title: caseData.title });

    
    res.status(201).json({
      success: true,
      data: newCase,
      message: 'Case created successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Error creating case:', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to create case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * PUT /cases/:id
 * Update an existing case
 */
exports.updateCase = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const updates = req.body;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Prepare update data
    const updateData = {
      updatedAt: new Date().toISOString(),
      version: (caseData.version || 1) + 1
    };
    
    // Only update provided fields
    const allowedFields = [
      'title', 'description', 'status', 'type', 'priority', 
      'clientName', 'clientEmail', 'dueDate'
    ];
    
    allowedFields.forEach(field => {
      if (updates[field] !== undefined) {
        updateData[field] = typeof updates[field] === 'string' 
          ? updates[field].trim() 
          : updates[field];
      }
    });

    await firestore.collection(CASES_COLLECTION).doc(id).update(updateData);
    
    const updatedDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    const updatedData = { id: updatedDoc.id, ...updatedDoc.data() };

    // Log activity
    await logCaseActivity(id, req.user.uid, 'case_updated', {
      updatedFields: Object.keys(updates),
      previousStatus: caseData.status,
      newStatus: updateData.status
    });

    writeLog('INFO', 'Case updated', { caseId: id, userId: req.user.uid });
    
    res.json({
      success: true,
      data: updatedData,
      message: 'Case updated successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to update case:', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to update case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * DELETE /cases/:id
 * Delete a case (soft delete)
 */
exports.deleteCase = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Soft delete - update status to deleted
    await firestore.collection(CASES_COLLECTION).doc(id).update({
      status: 'deleted',
      deletedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: (caseData.version || 1) + 1
    });

    // Log activity
    await logCaseActivity(id, req.user.uid, 'case_deleted', {
      title: caseData.title,
      previousStatus: caseData.status
    });

    writeLog('INFO', 'Case deleted', { caseId: id, userId: req.user.uid });
    
    res.json({
      success: true,
      message: 'Case deleted successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to delete case:', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to delete case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /cases/:id/analyze
 * Trigger AI analysis for a case
 */
exports.runCaseAnalysis = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Check if case has documents
    const docsSnapshot = await firestore
      .collection(DOCUMENTS_COLLECTION)
      .where('caseId', '==', id)
      .where('status', '!=', 'deleted')
      .get();
      
    if (docsSnapshot.empty) {
      return res.status(400).json({ 
        success: false,
        error: 'Cannot analyze case without documents',
        timestamp: new Date().toISOString()
      });
    }

    // Check if analysis is already in progress
    if (caseData.analysisStatus === 'processing') {
      return res.status(409).json({
        success: false,
        error: 'Analysis already in progress',
        timestamp: new Date().toISOString()
      });
    }

    // Publish message to trigger case analysis
    const messageData = {
      caseId: id,
      userId: req.user.uid,
      timestamp: new Date().toISOString(),
      documentCount: docsSnapshot.size,
      analysisType: req.body.analysisType || 'full'
    };

        // Publish message to Pub/Sub (topic configured by env)
    try {
      const topic = pubsub.topic(CASE_ANALYSIS_TOPIC);
      // Use publishMessage for structured attributes if desired
      await topic.publishMessage({
        json: messageData,
        attributes: {
          origin: 'case-service',
          userId: req.user.uid
        }
      });

      writeLog('INFO', 'Published case analysis message', { caseId: id, topic: CASE_ANALYSIS_TOPIC, userId: req.user.uid });
    } catch (pubErr) {
      writeLog('ERROR', 'Failed to publish Pub/Sub message', { caseId: id, error: pubErr.message });
      return res.status(500).json({
        success: false,
        error: 'Failed to trigger analysis process',
        timestamp: new Date().toISOString()
      });
    }

    // Update case analysis status and count (only after successful enqueue)
    await firestore.collection(CASES_COLLECTION).doc(id).update({
      analysisCount: (caseData.analysisCount || 0) + 1,
      analysisStatus: 'processing',
      lastAnalysisStartedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: (caseData.version || 1) + 1
    });


    // Log activity
    await logCaseActivity(id, req.user.uid, 'analysis_started', {
      documentCount: docsSnapshot.size,
      analysisType: messageData.analysisType
    });

    writeLog('INFO', 'Case analysis triggered', { userId: req.user.uid, caseId: id });
    
    res.json({ 
      success: true,
      data: {
        caseId: id,
        documentCount: docsSnapshot.size,
        status: 'processing',
        estimatedCompletionTime: '5-10 minutes'
      },
      message: 'Case analysis started successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to trigger case analysis', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to start case analysis',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /cases/:id/stats
 * Get detailed statistics for a specific case
 */
exports.getCaseStats = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Get document statistics
    const docsSnapshot = await firestore
      .collection(DOCUMENTS_COLLECTION)
      .where('caseId', '==', id)
      .where('status', '!=', 'deleted')
      .get();

    let totalSize = 0;
    let totalPages = 0;
    const documentTypes = {};
    const documents = [];

    docsSnapshot.forEach(doc => {
      const docData = doc.data();
      totalSize += docData.size || 0;
      totalPages += docData.pageCount || 0;
      
      const extension = docData.filename.split('.').pop().toLowerCase();
      documentTypes[extension] = (documentTypes[extension] || 0) + 1;
      
      documents.push({
        id: doc.id,
        filename: docData.filename,
        size: docData.size,
        uploadedAt: docData.uploadedAt,
        status: docData.status
      });
    });

    // Get activity count
    const activitiesSnapshot = await firestore
      .collection(CASE_ACTIVITIES_COLLECTION)
      .where('caseId', '==', id)
      .get();

    // Get notes count
    const notesSnapshot = await firestore
      .collection(CASE_NOTES_COLLECTION)
      .where('caseId', '==', id)
      .get();

    const stats = {
      caseId: id,
      basic: {
        title: caseData.title,
        status: caseData.status,
        type: caseData.type,
        priority: caseData.priority,
        createdAt: caseData.createdAt,
        updatedAt: caseData.updatedAt
      },
      documents: {
        count: docsSnapshot.size,
        totalSize,
        totalPages,
        types: documentTypes,
        recentDocuments: documents.slice(0, 5)
      },
      analysis: {
        count: caseData.analysisCount || 0,
        lastAnalyzedAt: caseData.lastAnalyzedAt,
        status: caseData.analysisStatus || 'none'
      },
      activity: {
        totalActivities: activitiesSnapshot.size,
        totalNotes: notesSnapshot.size
      },
      timeline: {
        created: caseData.createdAt,
        lastUpdated: caseData.updatedAt,
        dueDate: caseData.dueDate
      }
    };

    res.json({
      success: true,
      data: stats,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Error getting case stats:', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to get case statistics',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /cases/stats
 * Get overall case statistics for the user
 */
exports.getCaseStatistics = async (req, res) => {
  try {
    const userId = req.user.uid;
    
    // Get all user's cases
    const casesSnapshot = await firestore
      .collection(CASES_COLLECTION)
      .where('createdBy', '==', userId)
      .where('status', '!=', 'deleted')
      .get();

    const stats = {
      totalCases: casesSnapshot.size,
      byStatus: {},
      byType: {},
      byPriority: {},
      recentActivity: {
        casesCreatedThisMonth: 0,
        casesUpdatedThisWeek: 0
      }
    };

    const now = new Date();
    const thisMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const thisWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    casesSnapshot.forEach(doc => {
      const caseData = doc.data();
      
      // Count by status
      stats.byStatus[caseData.status] = (stats.byStatus[caseData.status] || 0) + 1;
      
      // Count by type
      stats.byType[caseData.type] = (stats.byType[caseData.type] || 0) + 1;
      
      // Count by priority
      stats.byPriority[caseData.priority] = (stats.byPriority[caseData.priority] || 0) + 1;
      
      // Recent activity
      const createdAt = new Date(caseData.createdAt);
      const updatedAt = new Date(caseData.updatedAt);
      
      if (createdAt >= thisMonth) {
        stats.recentActivity.casesCreatedThisMonth++;
      }
      
      if (updatedAt >= thisWeek) {
        stats.recentActivity.casesUpdatedThisWeek++;
      }
    });

    res.json({
      success: true,
      data: stats,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Error getting case statistics:', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to get case statistics',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /cases/:id/duplicate
 * Create a duplicate of an existing case
 */
exports.duplicateCase = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Get original case
    const originalDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!originalDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const originalData = originalDoc.data();
    if (originalData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Create duplicate case data
    const now = new Date().toISOString();
    const duplicateData = {
      ...originalData,
      title: `${originalData.title} (Copy)`,
      status: 'active',
      createdAt: now,
      updatedAt: now,
      documentCount: 0,
      analysisCount: 0,
      version: 1,
      duplicatedFrom: id,
      duplicatedAt: now
    };

    // Remove fields that shouldn't be duplicated
    delete duplicateData.deletedAt;
    delete duplicateData.lastAnalyzedAt;
    delete duplicateData.analysisStatus;

    const docRef = await firestore.collection(CASES_COLLECTION).add(duplicateData);
    const newCase = { id: docRef.id, ...duplicateData };

    // Log activity
    await logCaseActivity(docRef.id, req.user.uid, 'case_duplicated', {
      originalCaseId: id,
      originalTitle: originalData.title
    });

    writeLog('INFO', 'Case duplicated', { originalCaseId: id, newCaseId: docRef.id, userId: req.user.uid });
    
    res.status(201).json({
      success: true,
      data: newCase,
      message: 'Case duplicated successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to duplicate case', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to duplicate case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /cases/:id/archive
 * Archive a case
 */
exports.archiveCase = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    await firestore.collection(CASES_COLLECTION).doc(id).update({
      status: 'archived',
      archivedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: (caseData.version || 1) + 1
    });

    // Log activity
    await logCaseActivity(id, req.user.uid, 'case_archived', {
      previousStatus: caseData.status
    });

    res.json({
      success: true,
      message: 'Case archived successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to archive case', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to archive case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /cases/:id/restore
 * Restore an archived case
 */
exports.restoreCase = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    await firestore.collection(CASES_COLLECTION).doc(id).update({
      status: 'active',
      restoredAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: (caseData.version || 1) + 1
    });

    // Log activity
    await logCaseActivity(id, req.user.uid, 'case_restored', {
      previousStatus: caseData.status
    });

    res.json({
      success: true,
      message: 'Case restored successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to restore case', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to restore case',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /cases/:id/timeline
 * Get case activity timeline
 */
exports.getCaseTimeline = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { limit = 50 } = req.query;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Get activities
    const activitiesSnapshot = await firestore
      .collection(CASE_ACTIVITIES_COLLECTION)
      .where('caseId', '==', id)
      .orderBy('timestamp', 'desc')
      .limit(parseInt(limit))
      .get();

    const timeline = [];
    activitiesSnapshot.forEach(doc => {
      timeline.push({ id: doc.id, ...doc.data() });
    });

    res.json({
      success: true,
      data: {
        caseId: id,
        timeline,
        count: timeline.length
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to get case timeline', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to get case timeline',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /cases/:id/notes
 * Add a note to a case
 */
exports.addCaseNote = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { content, type = 'general' } = req.body;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    const noteData = {
      caseId: id,
      content: content.trim(),
      type,
      createdBy: req.user.uid,
      createdAt: new Date().toISOString()
    };

    const noteRef = await firestore.collection(CASE_NOTES_COLLECTION).add(noteData);
    const newNote = { id: noteRef.id, ...noteData };

    // Log activity
    await logCaseActivity(id, req.user.uid, 'note_added', {
      noteType: type,
      noteId: noteRef.id
    });

    res.status(201).json({
      success: true,
      data: newNote,
      message: 'Note added successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to add case note', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to add note',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /cases/:id/notes
 * Get all notes for a case
 */
exports.getCaseNotes = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { limit = 50, type } = req.query;
    
    // Check if case exists and user has permission
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(id).get();
    if (!caseDoc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Case not found',
        timestamp: new Date().toISOString()
      });
    }
    
    const caseData = caseDoc.data();
    if (caseData.createdBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    let query = firestore
      .collection(CASE_NOTES_COLLECTION)
      .where('caseId', '==', id);

    if (type) {
      query = query.where('type', '==', type);
    }

    query = query.orderBy('createdAt', 'desc').limit(parseInt(limit));

    const snapshot = await query.get();
    const notes = [];
    snapshot.forEach(doc => {
      notes.push({ id: doc.id, ...doc.data() });
    });

    res.json({
      success: true,
      data: {
        caseId: id,
        notes,
        count: notes.length,
        filters: { type }
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR', 'Failed to get case notes', { error: error.message });
    res.status(500).json({ 
      success: false,
      error: 'Failed to get case notes',
      timestamp: new Date().toISOString()
    });
  }
};