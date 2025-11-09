// shared/nodejs/firestore-client.js
const { Firestore, FieldValue, Timestamp } = require('@google-cloud/firestore');
const { v4: uuidv4 } = require('uuid');

/**
 * Firestore Client Wrapper for Legal Case AI
 * Provides standardized database operations across all services
 */
class FirestoreClient {
  constructor(projectId = null, databaseId = '(default)') {
    this.projectId = projectId || process.env.GOOGLE_CLOUD_PROJECT;
    this.databaseId = databaseId;
    
    // Initialize Firestore
    this.db = new Firestore({
  projectId: this.projectId,
  databaseId: this.databaseId,
  ignoreUndefinedProperties: true // ✅ Skip undefined fields instead of erroring
});

    
    // Collection references for easy access
    this.collections = {
      cases: this.db.collection('cases'),
      documents: this.db.collection('documents'),
      extractedDocuments: this.db.collection('extracted_documents'),
      documentAnalysis: this.db.collection('document_analysis'),
      caseAnalysis: this.db.collection('case_analysis'),
      chatMessages: this.db.collection('chat_messages'),
      users: this.db.collection('users'),
      userActivities: this.db.collection('user_activities'),
      pdfReports: this.db.collection('pdf_reports'),
      extractionErrors: this.db.collection('extraction_errors'),
      systemLogs: this.db.collection('system_logs'),
      notifications: this.db.collection('notifications')
    };
    
    console.log(`✅ Firestore client initialized for project: ${this.projectId}`);
  }

  /**
   * Test database connection
   */
  async testConnection() {
    try {
      // Try to read from a collection to test connection
      await this.collections.cases.limit(1).get();
      console.log('✅ Firestore connection test successful');
      return true;
    } catch (error) {
      console.error('❌ Firestore connection test failed:', error);
      throw error;
    }
  }

  // ==================== CASE OPERATIONS ====================

  /**
   * Create a new case
   */
  async createCase(caseData) {
    try {
      const now = Timestamp.now();
      const caseId = uuidv4();
      
      const newCase = {
        id: caseId,
        title: caseData.title,
        type: caseData.type || 'general',
        description: caseData.description || '',
        status: 'active',
        priority: caseData.priority || 'medium',
        createdBy: caseData.createdBy,
        createdAt: now,
        updatedAt: now,
        documentCount: 0,
        analysisCount: 0,
        extractionStatus: 'pending',
        analysisStatus: 'pending',
        tags: caseData.tags || [],
        metadata: caseData.metadata || {}
      };

      const docRef = this.collections.cases.doc(caseId);
      await docRef.set(newCase);
      
      // Log activity
      await this.logUserActivity(caseData.createdBy, 'case_created', {
        caseId,
        caseTitle: caseData.title
      });

      console.log(`✅ Case created: ${caseId}`);
      return { id: caseId, ...newCase };
    } catch (error) {
      console.error('❌ Error creating case:', error);
      throw error;
    }
  }

  /**
   * Get case by ID
   */
  async getCase(caseId) {
    try {
      const doc = await this.collections.cases.doc(caseId).get();
      
      if (!doc.exists) {
        return null;
      }

      return { id: doc.id, ...doc.data() };
    } catch (error) {
      console.error(`❌ Error getting case ${caseId}:`, error);
      throw error;
    }
  }

  /**
   * Update case
   */
  async updateCase(caseId, updateData) {
    try {
      const updates = {
        ...updateData,
        updatedAt: Timestamp.now()
      };

      await this.collections.cases.doc(caseId).update(updates);
      
      console.log(`✅ Case updated: ${caseId}`);
      return true;
    } catch (error) {
      console.error(`❌ Error updating case ${caseId}:`, error);
      throw error;
    }
  }

  /**
   * Get cases for user with pagination
   */
  async getUserCases(userId, options = {}) {
    try {
      const {
        limit = 20,
        offset = 0,
        orderBy = 'updatedAt',
        orderDirection = 'desc',
        status = null,
        type = null
      } = options;

      let query = this.collections.cases
        .where('createdBy', '==', userId);

      if (status) {
        query = query.where('status', '==', status);
      }
      
      if (type) {
        query = query.where('type', '==', type);
      }

      query = query
        .orderBy(orderBy, orderDirection)
        .limit(limit)
        .offset(offset);

      const snapshot = await query.get();
      
      const cases = [];
      snapshot.forEach(doc => {
        cases.push({ id: doc.id, ...doc.data() });
      });

      return cases;
    } catch (error) {
      console.error(`❌ Error getting user cases for ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Delete case (soft delete)
   */
  async deleteCase(caseId, userId) {
    try {
      await this.collections.cases.doc(caseId).update({
        status: 'deleted',
        deletedAt: Timestamp.now(),
        deletedBy: userId,
        updatedAt: Timestamp.now()
      });

      // Log activity
      await this.logUserActivity(userId, 'case_deleted', { caseId });

      console.log(`✅ Case deleted: ${caseId}`);
      return true;
    } catch (error) {
      console.error(`❌ Error deleting case ${caseId}:`, error);
      throw error;
    }
  }

  // ==================== DOCUMENT OPERATIONS ====================

  /**
   * Create document record
   */
  async createDocument(documentData) {
    try {
      const now = Timestamp.now();
      const documentId = uuidv4();

      const newDocument = {
        id: documentId,
        filename: documentData.filename,
        originalName: documentData.originalName || documentData.filename,
        contentType: documentData.contentType,
        size: documentData.size,
        caseId: documentData.caseId,
        storageKey: documentData.storageKey,
        checksum: documentData.checksum || null,
        uploadedBy: documentData.uploadedBy,
        uploadedAt: now,
        createdAt: now,
        updatedAt: now,
        status: 'uploaded',
        extractionStatus: 'pending',
        analysisStatus: 'pending',
        description: documentData.description || '',
        tags: documentData.tags || [],
        version: 1,
        metadata: documentData.metadata || {}
      };

      const docRef = this.collections.documents.doc(documentId);
      await docRef.set(newDocument);

      // Update case document count
      await this.collections.cases.doc(documentData.caseId).update({
        documentCount: FieldValue.increment(1),
        updatedAt: now
      });

      // Log activity
      await this.logUserActivity(documentData.uploadedBy, 'document_uploaded', {
        documentId,
        filename: documentData.filename,
        caseId: documentData.caseId
      });

      console.log(`✅ Document created: ${documentId}`);
      return { id: documentId, ...newDocument };
    } catch (error) {
      console.error('❌ Error creating document:', error);
      throw error;
    }
  }

  /**
   * Get document by ID
   */
  async getDocument(documentId) {
    try {
      const doc = await this.collections.documents.doc(documentId).get();
      
      if (!doc.exists) {
        return null;
      }

      return { id: doc.id, ...doc.data() };
    } catch (error) {
      console.error(`❌ Error getting document ${documentId}:`, error);
      throw error;
    }
  }

  /**
   * Get documents for case
   */
  async getCaseDocuments(caseId, options = {}) {
  try {
    const {
      limit = 50,
      orderBy = 'uploadedAt',
      orderDirection = 'desc',
      status = null
    } = options;

    let query = this.collections.documents
      .where('caseId', '==', caseId);

    if (status) {
      query = query.where('status', '==', status);
    }

    query = query.orderBy(orderBy, orderDirection).limit(limit);

    const snapshot = await query.get();

    const documents = [];
    snapshot.forEach(doc => {
      const data = doc.data();
      if (!status && data.status === 'deleted') return; // filter deleted manually
      documents.push({ id: doc.id, ...data });
    });

    return documents;
  } catch (error) {
    console.error(`❌ Error getting case documents for ${caseId}:`, error);
    throw error;
  }
}


  /**
   * Update document status
   */
  async updateDocumentStatus(documentId, status, additionalData = {}) {
    try {
      const updates = {
        status,
        updatedAt: Timestamp.now(),
        ...additionalData
      };

      await this.collections.documents.doc(documentId).update(updates);
      
      console.log(`✅ Document status updated: ${documentId} -> ${status}`);
      return true;
    } catch (error) {
      console.error(`❌ Error updating document status ${documentId}:`, error);
      throw error;
    }
  }

  // ==================== EXTRACTED DOCUMENTS OPERATIONS ====================

  /**
   * Save extracted document data
   */
  async saveExtractedDocument(extractedData) {
    try {
      const now = Timestamp.now();
      const extractedId = uuidv4();

      const extractedDocument = {
        id: extractedId,
        documentId: extractedData.documentId,
        caseId: extractedData.caseId,
        filename: extractedData.filename,
        text: extractedData.text,
        pageCount: extractedData.pageCount || 0,
        wordCount: extractedData.wordCount || 0,
        characterCount: extractedData.characterCount || 0,
        title: extractedData.title || '',
        language: extractedData.language || 'unknown',
        confidence: extractedData.confidence || 0,
        method: extractedData.method || 'unknown',
        processingTime: extractedData.processingTime || 0,
        extractedBy: extractedData.extractedBy,
        createdAt: now,
        metadata: extractedData.metadata || {}
      };

      const docRef = this.collections.extractedDocuments.doc(extractedId);
      await docRef.set(extractedDocument);

      console.log(`✅ Extracted document saved: ${extractedId}`);
      return { id: extractedId, ...extractedDocument };
    } catch (error) {
      console.error('❌ Error saving extracted document:', error);
      throw error;
    }
  }

  /**
   * Get extracted document by document ID
   */
  async getExtractedDocument(documentId) {
    try {
      const snapshot = await this.collections.extractedDocuments
        .where('documentId', '==', documentId)
        .orderBy('createdAt', 'desc')
        .limit(1)
        .get();

      if (snapshot.empty) {
        return null;
      }

      const doc = snapshot.docs[0];
      return { id: doc.id, ...doc.data() };
    } catch (error) {
      console.error(`❌ Error getting extracted document for ${documentId}:`, error);
      throw error;
    }
  }

  // ==================== ANALYSIS OPERATIONS ====================

  /**
   * Save document analysis
   */
  async saveDocumentAnalysis(analysisData) {
    try {
      const now = Timestamp.now();
      const analysisId = uuidv4();

      const analysis = {
        id: analysisId,
        documentId: analysisData.documentId,
        caseId: analysisData.caseId,
        analysisType: analysisData.analysisType || 'full',
        summary: analysisData.summary || '',
        keyPoints: analysisData.keyPoints || [],
        legalRelevance: analysisData.legalRelevance || '',
        entities: analysisData.entities || {},
        sentiment: analysisData.sentiment || {},
        readability: analysisData.readability || {},
        recommendations: analysisData.recommendations || [],
        confidence: analysisData.confidence || 0,
        processingTime: analysisData.processingTime || 0,
        analyzedBy: analysisData.analyzedBy,
        analyzedAt: now,
        metadata: analysisData.metadata || {}
      };

      const docRef = this.collections.documentAnalysis.doc(analysisId);
      await docRef.set(analysis);

      console.log(`✅ Document analysis saved: ${analysisId}`);
      return { id: analysisId, ...analysis };
    } catch (error) {
      console.error('❌ Error saving document analysis:', error);
      throw error;
    }
  }

  /**
   * Save case analysis
   */
  async saveCaseAnalysis(analysisData) {
    try {
      const now = Timestamp.now();
      const analysisId = uuidv4();

      const analysis = {
        id: analysisId,
        caseId: analysisData.caseId,
        analysisType: analysisData.analysisType || 'comprehensive',
        executiveSummary: analysisData.executiveSummary || '',
        keyFindings: analysisData.keyFindings || [],
        strengthsWeaknesses: analysisData.strengthsWeaknesses || {},
        legalIssues: analysisData.legalIssues || [],
        recommendations: analysisData.recommendations || [],
        riskAssessment: analysisData.riskAssessment || {},
        timeline: analysisData.timeline || [],
        strategicAdvice: analysisData.strategicAdvice || '',
        confidence: analysisData.confidence || 0,
        processingTime: analysisData.processingTime || 0,
        documentCount: analysisData.documentCount || 0,
        analyzedBy: analysisData.analyzedBy,
        analyzedAt: now,
        version: '1.0',
        metadata: analysisData.metadata || {}
      };

      const docRef = this.collections.caseAnalysis.doc(analysisId);
      await docRef.set(analysis);

      // Update case analysis count
      await this.collections.cases.doc(analysisData.caseId).update({
        analysisCount: FieldValue.increment(1),
        lastAnalyzedAt: now,
        analysisStatus: 'completed',
        updatedAt: now
      });

      console.log(`✅ Case analysis saved: ${analysisId}`);
      return { id: analysisId, ...analysis };
    } catch (error) {
      console.error('❌ Error saving case analysis:', error);
      throw error;
    }
  }

  // ==================== CHAT OPERATIONS ====================

  /**
   * Save chat message
   */
  async saveChatMessage(messageData) {
    try {
      const now = Timestamp.now();
      const messageId = uuidv4();

      const message = {
        id: messageId,
        caseId: messageData.caseId,
        userId: messageData.userId,
        message: messageData.message,
        type: messageData.type || 'user', // 'user' or 'ai'
        agent: messageData.agent || null,
        confidence: messageData.confidence || null,
        timestamp: now,
        metadata: messageData.metadata || {}
      };

      const docRef = this.collections.chatMessages.doc(messageId);
      await docRef.set(message);

      return { id: messageId, ...message };
    } catch (error) {
      console.error('❌ Error saving chat message:', error);
      throw error;
    }
  }

  /**
   * Get chat messages for case
   */
  async getChatMessages(caseId, options = {}) {
    try {
      const {
        limit = 50,
        offset = 0,
        orderDirection = 'desc'
      } = options;

      const query = this.collections.chatMessages
        .where('caseId', '==', caseId)
        .orderBy('timestamp', orderDirection)
        .limit(limit)
        .offset(offset);

      const snapshot = await query.get();
      
      const messages = [];
      snapshot.forEach(doc => {
        messages.push({ id: doc.id, ...doc.data() });
      });

      return messages;
    } catch (error) {
      console.error(`❌ Error getting chat messages for case ${caseId}:`, error);
      throw error;
    }
  }

  /**
   * Clear chat messages for case
   */
  async clearChatMessages(caseId, userId) {
    try {
      const snapshot = await this.collections.chatMessages
        .where('caseId', '==', caseId)
        .get();

      const batch = this.db.batch();
      let deleteCount = 0;

      snapshot.forEach(doc => {
        batch.delete(doc.ref);
        deleteCount++;
      });

      await batch.commit();

      // Log activity
      await this.logUserActivity(userId, 'chat_cleared', {
        caseId,
        messageCount: deleteCount
      });

      console.log(`✅ Cleared ${deleteCount} chat messages for case ${caseId}`);
      return deleteCount;
    } catch (error) {
      console.error(`❌ Error clearing chat messages for case ${caseId}:`, error);
      throw error;
    }
  }

  // ==================== USER OPERATIONS ====================

  /**
   * Create or update user profile
   */
  async saveUserProfile(userData) {
    try {
      const now = Timestamp.now();
      const userId = userData.uid;

      const userProfile = {
        uid: userId,
        email: userData.email,
        displayName: userData.displayName || '',
        photoURL: userData.photoURL || '',
        role: userData.role || 'user',
        preferences: userData.preferences || {},
        lastLoginAt: now,
        updatedAt: now,
        createdAt: userData.createdAt || now,
        isActive: true,
        metadata: userData.metadata || {}
      };
  
      const sanitizedProfile = Object.fromEntries(
  Object.entries(userProfile).filter(([_, v]) => v !== undefined)
);

      const docRef = this.collections.users.doc(userId);
      await docRef.set(userProfile, { merge: true });

      console.log(`✅ User profile saved: ${userId}`);
      return userProfile;
    } catch (error) {
      console.error(`❌ Error saving user profile:`, error);
      throw error;
    }
  }

  /**
   * Get user profile
   */
  async getUserProfile(userId) {
    try {
      const doc = await this.collections.users.doc(userId).get();
      
      if (!doc.exists) {
        return null;
      }

      return { id: doc.id, ...doc.data() };
    } catch (error) {
      console.error(`❌ Error getting user profile ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Log user activity
   */
  async logUserActivity(userId, activity, details = {}) {
    try {
      const now = Timestamp.now();
      const activityId = uuidv4();

      const activityLog = {
        id: activityId,
        userId,
        activity,
        details,
        timestamp: now,
        ipAddress: details.ipAddress || null,
        userAgent: details.userAgent || null
      };

      const docRef = this.collections.userActivities.doc(activityId);
      await docRef.set(activityLog);

      return activityId;
    } catch (error) {
      console.error(`❌ Error logging user activity:`, error);
      // Don't throw error for logging failures
    }
  }

  // ==================== NOTIFICATION OPERATIONS ====================

  /**
   * Create notification
   */
  async createNotification(notificationData) {
    try {
      const now = Timestamp.now();
      const notificationId = uuidv4();

      const notification = {
        id: notificationId,
        userId: notificationData.userId,
        title: notificationData.title,
        message: notificationData.message,
        type: notificationData.type || 'info',
        caseId: notificationData.caseId || null,
        documentId: notificationData.documentId || null,
        isRead: false,
        createdAt: now,
        readAt: null,
        metadata: notificationData.metadata || {}
      };

      const docRef = this.collections.notifications.doc(notificationId);
      await docRef.set(notification);

      console.log(`✅ Notification created: ${notificationId}`);
      return { id: notificationId, ...notification };
    } catch (error) {
      console.error('❌ Error creating notification:', error);
      throw error;
    }
  }

  /**
   * Get user notifications
   */
  async getUserNotifications(userId, options = {}) {
    try {
      const {
        limit = 20,
        unreadOnly = false,
        orderDirection = 'desc'
      } = options;

      let query = this.collections.notifications
        .where('userId', '==', userId);

      if (unreadOnly) {
        query = query.where('isRead', '==', false);
      }

      query = query
        .orderBy('createdAt', orderDirection)
        .limit(limit);

      const snapshot = await query.get();
      
      const notifications = [];
      snapshot.forEach(doc => {
        notifications.push({ id: doc.id, ...doc.data() });
      });

      return notifications;
    } catch (error) {
      console.error(`❌ Error getting notifications for user ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Mark notification as read
   */
  async markNotificationRead(notificationId) {
    try {
      await this.collections.notifications.doc(notificationId).update({
        isRead: true,
        readAt: Timestamp.now()
      });

      return true;
    } catch (error) {
      console.error(`❌ Error marking notification read ${notificationId}:`, error);
      throw error;
    }
  }

  // ==================== UTILITY METHODS ====================

  /**
   * Get server timestamp
   */
  getServerTimestamp() {
    return FieldValue.serverTimestamp();
  }

  /**
   * Get current timestamp
   */
  getCurrentTimestamp() {
    return Timestamp.now();
  }

  /**
   * Create batch operation
   */
  createBatch() {
    return this.db.batch();
  }

  /**
   * Execute transaction
   */
  async runTransaction(updateFunction) {
    return this.db.runTransaction(updateFunction);
  }

  /**
   * Get collection reference
   */
  getCollection(collectionName) {
    return this.db.collection(collectionName);
  }

  /**
   * Close database connection
   */
  async close() {
    try {
      await this.db.terminate();
      console.log('✅ Firestore connection closed');
    } catch (error) {
      console.error('❌ Error closing Firestore connection:', error);
    }
  }
}

module.exports = FirestoreClient;