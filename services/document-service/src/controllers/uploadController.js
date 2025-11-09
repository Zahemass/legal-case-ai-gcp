// services/document-service/src/controllers/uploadController.js
const { Firestore } = require('@google-cloud/firestore');
const { PubSub } = require('@google-cloud/pubsub');
const { validationResult } = require('express-validator');
const { v4: uuidv4 } = require('uuid');
const mime = require('mime-types');
// ✅ Simple logging helper (prevents ReferenceError crashes)
const writeLog = (level, message, data = null) => {
  const timestamp = new Date().toISOString();
  const label = `[${timestamp}] [${level}]`;
  if (data instanceof Error) {
    console.error(`${label} ${message}`, data.message, data.stack);
  } else if (data) {
    console.log(`${label} ${message}`, data);
  } else {
    console.log(`${label} ${message}`);
  }
};


const storageService = require('../services/storageService');

const firestore = new Firestore();
const pubsub = new PubSub();

// Collections
const DOCUMENTS_COLLECTION = 'documents';
const CASES_COLLECTION = 'cases';
const DOCUMENT_ANALYSIS_COLLECTION = 'document_analysis';
const EXTRACTED_DOCUMENTS_COLLECTION = 'extracted_documents';

/**
 * Handle validation errors
 */
const handleValidationErrors = (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      success: false,
      error: 'Validation failed',
      details: errors.array(),
      timestamp: new Date().toISOString()
    });
  }
  return null;
};

/**
 * Validate file type using file-type library
 */
/**
 * Validate file type using file-type library (for CommonJS)
 */
const validateFileType = async (buffer, originalMimetype, filename) => {
  try {
    // ✅ Dynamic import inside function to avoid top-level await
    const { fileTypeFromBuffer } = await import('file-type');

    if (!buffer) {
      return { isValid: false, error: 'Missing file buffer' };
    }

    const detectedType = await fileTypeFromBuffer(buffer);

    // Fallback for text-based files
    if (!detectedType) {
      const extension = filename.split('.').pop().toLowerCase();
      const textExtensions = ['txt', 'csv', 'rtf'];
      if (textExtensions.includes(extension) && originalMimetype.startsWith('text/')) {
        return { isValid: true, detectedMime: originalMimetype };
      }
      return { isValid: false, error: 'Unknown file type' };
    }

    // ✅ Allowed MIME types
    const allowedMimes = [
      'application/pdf',
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
      'text/plain'
    ];

    if (allowedMimes.includes(detectedType.mime)) {
      return { isValid: true, detectedMime: detectedType.mime };
    }

    return { isValid: false, error: `File type ${detectedType.mime} not allowed` };
  } catch (error) {
    writeLog('ERROR','File type validation error:', error);
    return { isValid: false, error: 'File validation failed' };
  }
};


/**
 * GET /documents
 * Get all documents for the authenticated user
 */
exports.getDocuments = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { 
      caseId, 
      status, 
      type, 
      limit = 20, 
      offset = 0, 
      sortBy = 'uploadedAt', 
      order = 'desc',
      search 
    } = req.query;
    
    let query = firestore.collection(DOCUMENTS_COLLECTION);
    
    // Filter by user's documents only
    query = query.where('uploadedBy', '==', req.user.uid);
    
    // Apply filters
    if (caseId) {
      query = query.where('caseId', '==', caseId);
    }
    
    if (status) {
  query = query.where('status', '==', status);
} else {
  // Exclude deleted documents by default (Firestore workaround)
  query = query.where('status', 'in', ['uploaded', 'processing', 'extracted', 'analyzed', 'error']);
}
    
    if (type) {
      query = query.where('contentType', '==', type);
    }
    
    // Add sorting and pagination
    query = query.orderBy(sortBy, order)
                 .limit(parseInt(limit))
                 .offset(parseInt(offset));
    
    const snapshot = await query.get();
    
    let documents = [];
    snapshot.forEach(doc => {
      documents.push({ id: doc.id, ...doc.data() });
    });

    // Apply search filter if provided
    if (search) {
      const searchTerm = search.toLowerCase();
      documents = documents.filter(doc => 
        doc.filename.toLowerCase().includes(searchTerm) ||
        (doc.description && doc.description.toLowerCase().includes(searchTerm)) ||
        (doc.tags && doc.tags.some(tag => tag.toLowerCase().includes(searchTerm)))
      );
    }

    // Get total count for pagination
    const countQuery = firestore.collection(DOCUMENTS_COLLECTION)
      .where('uploadedBy', '==', req.user.uid)
      .where('status', '!=', 'deleted');
    
    const totalSnapshot = await countQuery.get();
    const totalCount = totalSnapshot.size;

    res.json({
      success: true,
      data: {
        documents,
        pagination: {
          limit: parseInt(limit),
          offset: parseInt(offset),
          total: totalCount,
          hasMore: totalCount > parseInt(offset) + documents.length
        },
        filters: {
          caseId,
          status,
          type,
          search
        }
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error getting documents:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to fetch documents',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/:id
 * Get a specific document by ID
 */
exports.getDocumentById = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const docData = doc.data();
    
    // Check if user has access to this document
    if (docData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    res.json({
      success: true,
      data: { id: doc.id, ...docData },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error getting document:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to fetch document',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /documents/upload
 * Upload one or more documents
 */
exports.uploadDocuments = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    if (!req.files || req.files.length === 0) {
      return res.status(400).json({ 
        success: false,
        error: 'No files provided',
        timestamp: new Date().toISOString()
      });
    }

    const { caseId, description = '', tags = [] } = req.body;
    
    // Parse tags if it's a string
    let parsedTags = [];
    try {
      parsedTags = typeof tags === 'string' ? JSON.parse(tags) : tags;
    } catch (e) {
      parsedTags = [];
    }

    // Verify case exists and user has access
    const caseDoc = await firestore.collection(CASES_COLLECTION).doc(caseId).get();
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
        error: 'Access denied to case',
        timestamp: new Date().toISOString()
      });
    }

    const uploadedDocuments = [];
    const errors = [];

    for (const file of req.files) {
      const fileId = uuidv4();
      
      try {
        // Validate file type
        const typeValidation = await validateFileType(file.buffer, file.mimetype, file.originalname);
        if (!typeValidation.isValid) {
          errors.push({
            filename: file.originalname,
            error: typeValidation.error
          });
          continue;
        }

        // Generate unique filename
        const timestamp = Date.now();
        const extension = file.originalname.split('.').pop();
        const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_');
        const fileName = `${caseId}/${timestamp}_${fileId}_${safeName}`;
        
        // Upload to Cloud Storage
        const uploadResult = await storageService.uploadFile(
  file.buffer,
  fileName,
  {
    contentType: typeValidation.detectedMime,
    metadata: {
      caseId,
      uploadedBy: req.user.uid,
      originalName: file.originalname,
      uploadId: fileId,
      uploadedAt: new Date().toISOString()
    }
  }
);


        // Save document metadata to Firestore
        const documentData = {
          caseId,
          filename: file.originalname,
          safeFilename: safeName,
          contentType: typeValidation.detectedMime,
          size: file.size,
          storageKey: fileName,
          storageUrl: uploadResult.storageUrl || uploadResult.gsUri,
          uploadedBy: req.user.uid,
          uploadedAt: new Date().toISOString(),
          description: description.trim(),
          tags: Array.isArray(parsedTags) ? parsedTags : [],
          status: 'uploaded',
          extractionStatus: 'pending',
          analysisStatus: 'pending',
          version: 1,
          checksum: uploadResult.checksum || null
        };

        const docRef = await firestore.collection(DOCUMENTS_COLLECTION).add(documentData);

        // Trigger text extraction
        const extractionMessage = {
          documentId: docRef.id,
          storageKey: fileName,
          caseId,
          contentType: typeValidation.detectedMime,
          filename: file.originalname,
          size: file.size,
          userId: req.user.uid
        };

        await pubsub.topic('document-extraction-trigger').publish(
          Buffer.from(JSON.stringify(extractionMessage))
        );

        const newDocument = { id: docRef.id, ...documentData };
        uploadedDocuments.push(newDocument);

        writeLog('Info', `Document uploaded: ${docRef.id} (${file.originalname}) for case ${caseId}`);

      } catch (fileError) {
        writeLog('Error', `Error uploading file ${file.originalname}: ${fileError.message}`);
        errors.push({
          filename: file.originalname,
          error: 'Upload failed',
          details: fileError.message
        });
      }
    }

    // Update case document count
    if (uploadedDocuments.length > 0) {
      const currentDocCount = await firestore
        .collection(DOCUMENTS_COLLECTION)
        .where('caseId', '==', caseId)
        .where('status', '!=', 'deleted')
        .get();

      await firestore.collection(CASES_COLLECTION).doc(caseId).update({
        documentCount: currentDocCount.size,
        updatedAt: new Date().toISOString()
      });
    }

    const response = {
      success: uploadedDocuments.length > 0,
      data: {
        documents: uploadedDocuments,
        caseId,
        summary: {
          totalFiles: req.files.length,
          uploaded: uploadedDocuments.length,
          failed: errors.length
        }
      },
      timestamp: new Date().toISOString()
    };

    if (errors.length > 0) {
      response.errors = errors;
      response.message = `${uploadedDocuments.length} files uploaded successfully, ${errors.length} failed`;
    } else {
      response.message = `All ${uploadedDocuments.length} files uploaded successfully`;
    }

    const statusCode = uploadedDocuments.length > 0 ? 201 : 400;
    res.status(statusCode).json(response);

  } catch (error) {
    writeLog('ERROR','Error uploading documents:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to upload documents',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * DELETE /documents/:id
 * Delete a document (soft delete)
 */
exports.deleteDocument = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Soft delete in Firestore (don't delete from storage immediately for recovery)
    await firestore.collection(DOCUMENTS_COLLECTION).doc(id).update({
      status: 'deleted',
      deletedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: (documentData.version || 1) + 1
    });

    // Update case document count
    const currentDocCount = await firestore
      .collection(DOCUMENTS_COLLECTION)
      .where('caseId', '==', documentData.caseId)
      .where('status', '!=', 'deleted')
      .get();

    await firestore.collection(CASES_COLLECTION).doc(documentData.caseId).update({
      documentCount: currentDocCount.size,
      updatedAt: new Date().toISOString()
    });

    writeLog('Info',`✅ Document deleted: ${id} (${documentData.filename})`);
    
    res.json({
      success: true,
      message: 'Document deleted successfully',
      data: {
        documentId: id,
        filename: documentData.filename
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error deleting document:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to delete document',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/:id/download
 * Download original document
 */
exports.downloadDocument = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Check if document is not deleted
    if (documentData.status === 'deleted') {
      return res.status(404).json({ 
        success: false,
        error: 'Document has been deleted',
        timestamp: new Date().toISOString()
      });
    }

    // Get signed URL for download
    const downloadUrl = await storageService.getSignedUrl(
      documentData.storageKey,
      'read',
      3600 // 1 hour expiry
    );

    res.json({
      success: true,
      data: {
        downloadUrl,
        filename: documentData.filename,
        contentType: documentData.contentType,
        size: documentData.size,
        expiresIn: 3600
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error generating download link:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to generate download link',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /documents/:id/analyze
 * Trigger AI analysis for a document
 */
exports.analyzeDocument = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { analysisType = 'full' } = req.body;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Check if document extraction is complete
    if (documentData.extractionStatus !== 'completed') {
      return res.status(400).json({ 
        success: false,
        error: 'Document extraction not completed yet',
        details: `Current status: ${documentData.extractionStatus}`,
        timestamp: new Date().toISOString()
      });
    }

    // Check if analysis is already in progress
    if (documentData.analysisStatus === 'processing') {
      return res.status(409).json({
        success: false,
        error: 'Analysis already in progress',
        timestamp: new Date().toISOString()
      });
    }

    // Trigger document analysis
    const analysisMessage = {
      documentId: id,
      caseId: documentData.caseId,
      storageKey: documentData.storageKey,
      filename: documentData.filename,
      contentType: documentData.contentType,
      userId: req.user.uid,
      analysisType,
      requestedAt: new Date().toISOString()
    };

    await pubsub.topic('document-analysis-trigger').publish(
      Buffer.from(JSON.stringify(analysisMessage))
    );

    // Update document analysis status
    await firestore.collection(DOCUMENTS_COLLECTION).doc(id).update({
      analysisStatus: 'processing',
      analysisStartedAt: new Date().toISOString(),
      analysisType,
      updatedAt: new Date().toISOString(),
      version: (documentData.version || 1) + 1
    });

    writeLog('Info',`✅ Document analysis triggered for document ${id} (${documentData.filename})`);
    
    res.json({ 
      success: true,
      data: {
        documentId: id,
        filename: documentData.filename,
        status: 'processing',
        analysisType,
        estimatedCompletionTime: '2-5 minutes'
      },
      message: 'Document analysis started successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error triggering document analysis:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to start document analysis',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/:id/analysis
 * Get document analysis results
 */
exports.getDocumentAnalysis = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Get analysis results
    const analysisQuery = await firestore
      .collection(DOCUMENT_ANALYSIS_COLLECTION)
      .where('documentId', '==', id)
      .orderBy('analyzedAt', 'desc')
      .limit(1)
      .get();

    if (analysisQuery.empty) {
      return res.status(404).json({
        success: false,
        error: 'No analysis found for this document',
        status: documentData.analysisStatus || 'pending',
        timestamp: new Date().toISOString()
      });
    }

    const analysisDoc = analysisQuery.docs[0];
    const analysisData = { id: analysisDoc.id, ...analysisDoc.data() };

    res.json({
      success: true,
      data: {
        document: {
          id: doc.id,
          filename: documentData.filename,
          contentType: documentData.contentType,
          uploadedAt: documentData.uploadedAt
        },
        analysis: analysisData,
        status: documentData.analysisStatus
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error getting document analysis:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to get document analysis',
      timestamp: new Date().toISOString()
    });
  }
};

// Continue with remaining methods...

/**
 * POST /documents/batch/analyze
 * Batch analyze multiple documents
 */
exports.batchAnalyzeDocuments = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { documentIds, analysisType = 'full' } = req.body;
    
    if (documentIds.length > 20) {
      return res.status(400).json({
        success: false,
        error: 'Maximum 20 documents allowed per batch',
        timestamp: new Date().toISOString()
      });
    }

    const results = [];

    for (const docId of documentIds) {
      try {
        const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(docId).get();
        
        if (!doc.exists) {
          results.push({ documentId: docId, error: 'Document not found' });
          continue;
        }

        const documentData = doc.data();
        
        if (documentData.uploadedBy !== req.user.uid) {
          results.push({ documentId: docId, error: 'Access denied' });
          continue;
        }

        if (documentData.extractionStatus !== 'completed') {
          results.push({ 
            documentId: docId, 
            error: 'Extraction not completed',
            status: documentData.extractionStatus 
          });
          continue;
        }

        if (documentData.analysisStatus === 'processing') {
          results.push({ 
            documentId: docId, 
            error: 'Analysis already in progress'
          });
          continue;
        }

        // Trigger analysis
        const analysisMessage = {
          documentId: docId,
          caseId: documentData.caseId,
          storageKey: documentData.storageKey,
          filename: documentData.filename,
          contentType: documentData.contentType,
          userId: req.user.uid,
          analysisType,
          batchId: uuidv4(),
          requestedAt: new Date().toISOString()
        };

        await pubsub.topic('document-analysis-trigger').publish(
          Buffer.from(JSON.stringify(analysisMessage))
        );

        await firestore.collection(DOCUMENTS_COLLECTION).doc(docId).update({
          analysisStatus: 'processing',
          analysisStartedAt: new Date().toISOString(),
          analysisType,
          updatedAt: new Date().toISOString(),
          version: (documentData.version || 1) + 1
        });

        results.push({ 
          documentId: docId, 
          filename: documentData.filename,
          status: 'processing' 
        });

      } catch (docError) {
        writeLog('ERROR',`❌ Error processing document ${docId}:`, docError);
        results.push({ documentId: docId, error: 'Processing failed' });
      }
    }

    const successCount = results.filter(r => !r.error).length;
    const errorCount = results.filter(r => r.error).length;

    writeLog('Info',`✅ Batch analysis: ${successCount} started, ${errorCount} failed`);

    res.json({
      success: successCount > 0,
      data: {
        results,
        summary: {
          total: documentIds.length,
          started: successCount,
          failed: errorCount
        },
        analysisType,
        estimatedCompletionTime: '5-15 minutes'
      },
      message: `Batch analysis initiated for ${successCount} documents`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error in batch analyze:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to initiate batch analysis',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /documents/batch/delete
 * Batch delete multiple documents
 */
exports.batchDeleteDocuments = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { documentIds } = req.body;
    
    if (documentIds.length > 50) {
      return res.status(400).json({
        success: false,
        error: 'Maximum 50 documents allowed per batch',
        timestamp: new Date().toISOString()
      });
    }

    const results = [];
    const caseUpdates = new Map(); // Track case document counts

    for (const docId of documentIds) {
      try {
        const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(docId).get();
        
        if (!doc.exists) {
          results.push({ documentId: docId, error: 'Document not found' });
          continue;
        }

        const documentData = doc.data();
        
        if (documentData.uploadedBy !== req.user.uid) {
          results.push({ documentId: docId, error: 'Access denied' });
          continue;
        }

        // Soft delete
        await firestore.collection(DOCUMENTS_COLLECTION).doc(docId).update({
          status: 'deleted',
          deletedAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          version: (documentData.version || 1) + 1
        });

        // Track case for count update
        if (!caseUpdates.has(documentData.caseId)) {
          caseUpdates.set(documentData.caseId, []);
        }
        caseUpdates.get(documentData.caseId).push(docId);

        results.push({ 
          documentId: docId, 
          filename: documentData.filename,
          status: 'deleted' 
        });

      } catch (docError) {
        writeLog('ERROR',`❌ Error deleting document ${docId}:`, docError);
        results.push({ documentId: docId, error: 'Deletion failed' });
      }
    }

    // Update case document counts
    for (const [caseId, deletedDocs] of caseUpdates) {
      try {
        const currentDocCount = await firestore
          .collection(DOCUMENTS_COLLECTION)
          .where('caseId', '==', caseId)
          .where('status', '!=', 'deleted')
          .get();

        await firestore.collection(CASES_COLLECTION).doc(caseId).update({
          documentCount: currentDocCount.size,
          updatedAt: new Date().toISOString()
        });
      } catch (updateError) {
        writeLog('ERROR',`❌ Error updating case ${caseId} document count:`, updateError);
      }
    }

    const successCount = results.filter(r => r.status === 'deleted').length;
    const errorCount = results.filter(r => r.error).length;

    writeLog('Info',`✅ Batch delete: ${successCount} deleted, ${errorCount} failed`);

    res.json({
      success: successCount > 0,
      data: {
        results,
        summary: {
          total: documentIds.length,
          deleted: successCount,
          failed: errorCount
        }
      },
      message: `Batch deletion completed: ${successCount} documents deleted`,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error in batch delete:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to complete batch deletion',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * PUT /documents/:id/metadata
 * Update document metadata
 */
exports.updateDocumentMetadata = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { filename, description, tags } = req.body;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Prepare update data
    const updateData = {
      updatedAt: new Date().toISOString(),
      version: (documentData.version || 1) + 1
    };

    if (filename !== undefined) {
      updateData.filename = filename.trim();
    }
    
    if (description !== undefined) {
      updateData.description = description.trim();
    }
    
    if (tags !== undefined) {
      updateData.tags = Array.isArray(tags) ? tags : [];
    }

    await firestore.collection(DOCUMENTS_COLLECTION).doc(id).update(updateData);
    
    const updatedDoc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    const updatedData = { id: updatedDoc.id, ...updatedDoc.data() };

    writeLog('Info',`✅ Document metadata updated: ${id}`);
    
    res.json({
      success: true,
      data: updatedData,
      message: 'Document metadata updated successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error updating document metadata:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to update document metadata',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * POST /documents/:id/extract
 * Trigger text extraction for a document
 */
exports.extractDocument = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Check if extraction is already in progress or completed
    if (documentData.extractionStatus === 'processing') {
      return res.status(409).json({
        success: false,
        error: 'Extraction already in progress',
        timestamp: new Date().toISOString()
      });
    }

    // Trigger text extraction
    const extractionMessage = {
      documentId: id,
      storageKey: documentData.storageKey,
      caseId: documentData.caseId,
      contentType: documentData.contentType,
      filename: documentData.filename,
      size: documentData.size,
      userId: req.user.uid,
      retryCount: 0,
      requestedAt: new Date().toISOString()
    };

    await pubsub.topic('document-extraction-trigger').publish(
      Buffer.from(JSON.stringify(extractionMessage))
    );

    // Update document extraction status
    await firestore.collection(DOCUMENTS_COLLECTION).doc(id).update({
      extractionStatus: 'processing',
      extractionStartedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: (documentData.version || 1) + 1
    });

    writeLog('Info',`✅ Document extraction triggered for document ${id} (${documentData.filename})`);
    
    res.json({ 
      success: true,
      data: {
        documentId: id,
        filename: documentData.filename,
        status: 'processing',
        estimatedCompletionTime: '1-3 minutes'
      },
      message: 'Document extraction started successfully',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error triggering document extraction:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to start document extraction',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/:id/extraction-status
 * Get document extraction status
 */
exports.getExtractionStatus = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    
    // Get document data
    const doc = await firestore.collection(DOCUMENTS_COLLECTION).doc(id).get();
    if (!doc.exists) {
      return res.status(404).json({ 
        success: false,
        error: 'Document not found',
        timestamp: new Date().toISOString()
      });
    }

    const documentData = doc.data();
    
    // Check if user has access to this document
    if (documentData.uploadedBy !== req.user.uid) {
      return res.status(403).json({ 
        success: false,
        error: 'Access denied',
        timestamp: new Date().toISOString()
      });
    }

    // Get extraction details if completed
    let extractionData = null;
    if (documentData.extractionStatus === 'completed') {
      const extractionQuery = await firestore
        .collection(EXTRACTED_DOCUMENTS_COLLECTION)
        .where('documentId', '==', id)
        .orderBy('createdAt', 'desc')
        .limit(1)
        .get();

      if (!extractionQuery.empty) {
        const extractionDoc = extractionQuery.docs[0];
        extractionData = extractionDoc.data();
      }
    }

    res.json({
      success: true,
      data: {
        documentId: id,
        filename: documentData.filename,
        extractionStatus: documentData.extractionStatus,
        extractionStartedAt: documentData.extractionStartedAt,
        extractionCompletedAt: documentData.extractionCompletedAt,
        extraction: extractionData ? {
          pageCount: extractionData.pageCount,
          textLength: extractionData.text ? extractionData.text.length : 0,
          language: extractionData.language,
          confidence: extractionData.confidence
        } : null
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error getting extraction status:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to get extraction status',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/stats
 * Get document statistics for the authenticated user
 */
exports.getDocumentStatistics = async (req, res) => {
  try {
    const userId = req.user.uid;
    
    // Get all user's documents
    const docsSnapshot = await firestore
      .collection(DOCUMENTS_COLLECTION)
      .where('uploadedBy', '==', userId)
      .where('status', '!=', 'deleted')
      .get();

    const stats = {
      totalDocuments: docsSnapshot.size,
      totalSize: 0,
      byStatus: {
        uploaded: 0,
        processing: 0,
        extracted: 0,
        analyzed: 0,
        error: 0
      },
      byType: {},
      recentActivity: {
        documentsUploadedThisWeek: 0,
        documentsAnalyzedThisWeek: 0
      },
      extraction: {
        completed: 0,
        pending: 0,
        processing: 0,
        failed: 0
      },
      analysis: {
        completed: 0,
        pending: 0,
        processing: 0,
        failed: 0
      }
    };

    const now = new Date();
    const thisWeek = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    docsSnapshot.forEach(doc => {
      const docData = doc.data();
      
      // Total size
      stats.totalSize += docData.size || 0;
      
      // Count by status
      const status = docData.status || 'uploaded';
      if (stats.byStatus[status] !== undefined) {
        stats.byStatus[status]++;
      }
      
      // Count by content type
      const contentType = docData.contentType || 'unknown';
      const category = contentType.split('/')[0];
      stats.byType[category] = (stats.byType[category] || 0) + 1;
      
      // Extraction status
      const extractionStatus = docData.extractionStatus || 'pending';
      if (stats.extraction[extractionStatus] !== undefined) {
        stats.extraction[extractionStatus]++;
      }
      
      // Analysis status
      const analysisStatus = docData.analysisStatus || 'pending';
      if (stats.analysis[analysisStatus] !== undefined) {
        stats.analysis[analysisStatus]++;
      }
      
      // Recent activity
      const uploadedAt = new Date(docData.uploadedAt);
      if (uploadedAt >= thisWeek) {
        stats.recentActivity.documentsUploadedThisWeek++;
      }
      
      if (docData.analysisCompletedAt) {
        const analyzedAt = new Date(docData.analysisCompletedAt);
        if (analyzedAt >= thisWeek) {
          stats.recentActivity.documentsAnalyzedThisWeek++;
        }
      }
    });

    res.json({
      success: true,
      data: stats,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    writeLog('ERROR','Error getting document statistics:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to get document statistics',
      timestamp: new Date().toISOString()
    });
  }
};