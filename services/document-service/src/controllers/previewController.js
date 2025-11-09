// services/document-service/src/controllers/previewController.js
const { Firestore } = require('@google-cloud/firestore');
const { validationResult } = require('express-validator');
const storageService = require('../services/storageService');

const firestore = new Firestore();

// Collections
const DOCUMENTS_COLLECTION = 'documents';
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
 * GET /documents/:id/preview
 * Get document preview/content
 */
exports.getDocumentPreview = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { format = 'text', maxLength = 5000 } = req.query;
    
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

    // Check if document is deleted
    if (documentData.status === 'deleted') {
      return res.status(404).json({ 
        success: false,
        error: 'Document has been deleted',
        timestamp: new Date().toISOString()
      });
    }

    let previewData = {
      documentId: id,
      filename: documentData.filename,
      contentType: documentData.contentType,
      size: documentData.size,
      uploadedAt: documentData.uploadedAt,
      extractionStatus: documentData.extractionStatus
    };

    // If text format requested and extraction is completed
    if (format === 'text' && documentData.extractionStatus === 'completed') {
      const extractedDocsRef = firestore.collection(EXTRACTED_DOCUMENTS_COLLECTION);
      const extractionSnapshot = await extractedDocsRef
        .where('documentId', '==', id)
        .orderBy('createdAt', 'desc')
        .limit(1)
        .get();
      
      if (!extractionSnapshot.empty) {
        const extractedDoc = extractionSnapshot.docs[0].data();
        
        let previewText = extractedDoc.text || '';
        const isPreviewTruncated = previewText.length > parseInt(maxLength);
        
        if (isPreviewTruncated) {
          previewText = previewText.substring(0, parseInt(maxLength)) + '...';
        }

        previewData.textPreview = {
          content: previewText,
          fullLength: extractedDoc.text ? extractedDoc.text.length : 0,
          previewLength: previewText.length,
          isTruncated: isPreviewTruncated,
          pageCount: extractedDoc.pageCount || 0,
          language: extractedDoc.language || 'unknown',
          confidence: extractedDoc.confidence || 0
        };
      } else {
        previewData.textPreview = {
          error: 'Extracted text not found',
          status: documentData.extractionStatus
        };
      }
    }

    // If image/thumbnail format requested
    if (format === 'thumbnail' || format === 'image') {
      // For image files, provide direct access
      if (documentData.contentType.startsWith('image/')) {
        try {
          const thumbnailUrl = await storageService.getSignedUrl(
            documentData.storageKey,
            'read',
            3600 // 1 hour expiry
          );
          
          previewData.imagePreview = {
            thumbnailUrl,
            originalUrl: thumbnailUrl,
            contentType: documentData.contentType,
            expiresIn: 3600
          };
        } catch (error) {
          console.error('Error generating image preview:', error);
          previewData.imagePreview = {
            error: 'Failed to generate image preview'
          };
        }
      } else {
        // For non-image files, check if thumbnail exists
        const thumbnailKey = `thumbnails/${documentData.storageKey}.jpg`;
        try {
          const thumbnailExists = await storageService.fileExists(thumbnailKey);
          if (thumbnailExists) {
            const thumbnailUrl = await storageService.getSignedUrl(
              thumbnailKey,
              'read',
              3600
            );
            
            previewData.imagePreview = {
              thumbnailUrl,
              contentType: 'image/jpeg',
              expiresIn: 3600,
              generated: true
            };
          } else {
            previewData.imagePreview = {
              error: 'Thumbnail not available for this document type'
            };
          }
        } catch (error) {
          console.error('Error checking thumbnail:', error);
          previewData.imagePreview = {
            error: 'Failed to check thumbnail availability'
          };
        }
      }
    }

    // If raw/download format requested
    if (format === 'raw' || format === 'download') {
      try {
        const downloadUrl = await storageService.getSignedUrl(
          documentData.storageKey,
          'read',
          3600
        );
        
        previewData.downloadPreview = {
          downloadUrl,
          filename: documentData.filename,
          contentType: documentData.contentType,
          size: documentData.size,
          expiresIn: 3600
        };
      } catch (error) {
        console.error('Error generating download preview:', error);
        previewData.downloadPreview = {
          error: 'Failed to generate download link'
        };
      }
    }

    // If metadata format requested
    if (format === 'metadata') {
      previewData.metadata = {
        filename: documentData.filename,
        originalName: documentData.filename,
        contentType: documentData.contentType,
        size: documentData.size,
        uploadedAt: documentData.uploadedAt,
        uploadedBy: documentData.uploadedBy,
        caseId: documentData.caseId,
        description: documentData.description || '',
        tags: documentData.tags || [],
        version: documentData.version || 1,
        checksum: documentData.checksum,
        status: documentData.status,
        extractionStatus: documentData.extractionStatus,
        analysisStatus: documentData.analysisStatus,
        createdAt: documentData.createdAt,
        updatedAt: documentData.updatedAt
      };
    }

    res.json({
      success: true,
      data: previewData,
      requestedFormat: format,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting document preview:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to get document preview',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/:id/preview/full-text
 * Get full extracted text for a document
 */
exports.getFullDocumentText = async (req, res) => {
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

    // Check if extraction is completed
    if (documentData.extractionStatus !== 'completed') {
      return res.status(400).json({ 
        success: false,
        error: 'Text extraction not completed',
        status: documentData.extractionStatus,
        timestamp: new Date().toISOString()
      });
    }

    // Get extracted text
    const extractedDocsRef = firestore.collection(EXTRACTED_DOCUMENTS_COLLECTION);
    const extractionSnapshot = await extractedDocsRef
      .where('documentId', '==', id)
      .orderBy('createdAt', 'desc')
      .limit(1)
      .get();
    
    if (extractionSnapshot.empty) {
      return res.status(404).json({
        success: false,
        error: 'Extracted text not found',
        timestamp: new Date().toISOString()
      });
    }

    const extractedDoc = extractionSnapshot.docs[0].data();

    res.json({
      success: true,
      data: {
        documentId: id,
        filename: documentData.filename,
        extractedText: extractedDoc.text || '',
        metadata: {
          pageCount: extractedDoc.pageCount || 0,
          textLength: extractedDoc.text ? extractedDoc.text.length : 0,
          language: extractedDoc.language || 'unknown',
          confidence: extractedDoc.confidence || 0,
          extractedAt: extractedDoc.createdAt,
          extractionMethod: extractedDoc.method || 'unknown'
        }
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error getting full document text:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to get document text',
      timestamp: new Date().toISOString()
    });
  }
};

/**
 * GET /documents/:id/preview/search
 * Search within document text
 */
exports.searchInDocument = async (req, res) => {
  try {
    const validationError = handleValidationErrors(req, res);
    if (validationError) return validationError;

    const { id } = req.params;
    const { query: searchQuery, caseSensitive = false, wholeWord = false, maxResults = 50 } = req.query;
    
    if (!searchQuery || searchQuery.trim().length === 0) {
      return res.status(400).json({ 
        success: false,
        error: 'Search query is required',
        timestamp: new Date().toISOString()
      });
    }

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

    // Check if extraction is completed
    if (documentData.extractionStatus !== 'completed') {
      return res.status(400).json({ 
        success: false,
        error: 'Text extraction not completed',
        status: documentData.extractionStatus,
        timestamp: new Date().toISOString()
      });
    }

    // Get extracted text
    const extractedDocsRef = firestore.collection(EXTRACTED_DOCUMENTS_COLLECTION);
    const extractionSnapshot = await extractedDocsRef
      .where('documentId', '==', id)
      .orderBy('createdAt', 'desc')
      .limit(1)
      .get();
    
    if (extractionSnapshot.empty) {
      return res.status(404).json({
        success: false,
        error: 'Extracted text not found',
        timestamp: new Date().toISOString()
      });
    }

    const extractedDoc = extractionSnapshot.docs[0].data();
    const text = extractedDoc.text || '';

    // Perform search
    const results = [];
    let searchRegex;
    
    try {
      let regexFlags = 'g';
      if (!caseSensitive) regexFlags += 'i';
      
      let pattern = searchQuery.trim();
      if (wholeWord) {
        pattern = `\\b${pattern}\\b`;
      }
      
      searchRegex = new RegExp(pattern, regexFlags);
    } catch (regexError) {
      return res.status(400).json({
        success: false,
        error: 'Invalid search pattern',
        details: regexError.message,
        timestamp: new Date().toISOString()
      });
    }

    let match;
    let matchCount = 0;
    const contextLength = 100; // Characters before and after match

    while ((match = searchRegex.exec(text)) !== null && matchCount < parseInt(maxResults)) {
      const startIndex = Math.max(0, match.index - contextLength);
      const endIndex = Math.min(text.length, match.index + match[0].length + contextLength);
      
      const contextBefore = text.substring(startIndex, match.index);
      const contextAfter = text.substring(match.index + match[0].length, endIndex);
      
      results.push({
        match: match[0],
        index: match.index,
        context: {
          before: contextBefore,
          match: match[0],
          after: contextAfter,
          full: text.substring(startIndex, endIndex)
        },
        position: {
          character: match.index,
          line: text.substring(0, match.index).split('\n').length
        }
      });
      
      matchCount++;
    }

    res.json({
      success: true,
      data: {
        documentId: id,
        filename: documentData.filename,
        searchQuery,
        searchOptions: {
          caseSensitive: caseSensitive === 'true',
          wholeWord: wholeWord === 'true',
          maxResults: parseInt(maxResults)
        },
        results,
        summary: {
          totalMatches: results.length,
          hasMore: matchCount >= parseInt(maxResults),
          documentLength: text.length,
          searchTime: Date.now() // Could be calculated properly
        }
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error searching in document:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to search in document',
      timestamp: new Date().toISOString()
    });
  }
};