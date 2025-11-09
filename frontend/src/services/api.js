// frontend/services/api.js
import { auth } from '../firebase';

/* ---------------------------------------------------------
 * ⚙️ Firebase Auth Helpers for Cloud Run + Local backend
 * --------------------------------------------------------- */
// Cloud Run = case-service
// Local (for now) = document-service
const CASE_API_URL = import.meta.env.VITE_CASE_API_URL || 'http://localhost:8080';
const DOCUMENT_API_URL = import.meta.env.VITE_DOCUMENT_API_URL || 'http://localhost:8080';
const ANALYSIS_API_URL = import.meta.env.VITE_ANALYSIS_API_URL || 'http://localhost:8080';


async function getAuthToken() {
  const user = auth.currentUser;
  if (!user) throw new Error('User not authenticated');
  return await user.getIdToken();
}

/**
 * Generic request helper for both services
 */
async function request(baseUrl, path, options = {}) {
  const token = await getAuthToken();

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...options.headers,
  };

  const res = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorText = await res.text();
    console.error(`❌ API Error ${res.status}:`, errorText);
    throw new Error(`Request failed: ${res.status} ${res.statusText}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

/* ---------------------------------------------------------
 * ✅ CASE MANAGEMENT (Cloud Run: case-service)
 * --------------------------------------------------------- */

/**
 * Get all cases for the logged-in user
 */
export async function getCases() {
  try {
    return await request(CASE_API_URL, '/cases', { method: 'GET' });
  } catch (err) {
    console.error('Error fetching cases:', err);
    throw err;
  }
}

/**
 * Get a single case by ID
 */
export async function getCaseById(caseId) {
  if (!caseId) throw new Error('Case ID is required');
  return request(CASE_API_URL, `/cases/${caseId}`, { method: 'GET' });
}

/**
 * Create a new case
 */
export async function createCase(caseData) {
  if (!caseData.title) throw new Error('Case title is required');

  try {
    const newCase = await request(CASE_API_URL, '/cases', {
      method: 'POST',
      body: JSON.stringify(caseData),
    });
    console.log('✅ Case created successfully:', newCase);
    return newCase;
  } catch (err) {
    console.error('❌ Error creating case:', err);
    throw err;
  }
}

/**
 * Run AI analysis on a case
 */
export async function runCaseAnalysis(caseId) {
  if (!caseId) throw new Error('Case ID is required');

  try {
    const result = await request(CASE_API_URL, `/cases/${caseId}/analyze`, { method: 'POST' });
    console.log('✅ Analysis triggered:', result);
    return result;
  } catch (err) {
    console.error('❌ Error running analysis:', err);
    throw err;
  }
}

/* ---------------------------------------------------------
 * 📄 DOCUMENT MANAGEMENT (Local: document-service)
 * --------------------------------------------------------- */

/**
 * Get all documents for a specific case
 */
/**
 * Get all documents for a specific case
 */
export async function getDocuments(caseId) {
  if (!caseId) throw new Error('Case ID is required');
  try {
    const response = await request(DOCUMENT_API_URL, `/documents?caseId=${caseId}`, {
      method: 'GET',
    });

    // ✅ Firestore response format:
    // { success: true, data: { documents: [ ... ], caseId: "..." } }
    const docs = response?.data?.documents || [];

    console.log('✅ Documents fetched (flattened):', docs);
    return docs;
  } catch (error) {
    console.error('❌ Error fetching documents:', error);
    return [];
  }
}


/**
 * Upload a document for a case
 */
export async function uploadDocument(file, caseId, userId) {
  try {
    const token = await getAuthToken();
    const formData = new FormData();
    formData.append('files', file);
    formData.append('caseId', caseId);
    formData.append('userId', userId);

    const res = await fetch(`${DOCUMENT_API_URL}/documents/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    if (!res.ok) {
      const errorText = await res.text();
      console.error('❌ Upload failed:', errorText);
      throw new Error(`Upload failed: ${res.status} ${res.statusText}`);
    }

    const uploaded = await res.json();
    console.log('✅ Document uploaded:', uploaded);
    return uploaded;
  } catch (error) {
    console.error('❌ Error uploading document:', error);
    throw error;
  }
}

/**
 * Get document preview content
 */
export async function getDocumentPreview(documentId) {
  if (!documentId) throw new Error('Document ID is required');
  try {
    const preview = await request(DOCUMENT_API_URL, `/documents/${documentId}/preview`, { method: 'GET' });
    console.log('✅ Preview loaded:', preview);
    return preview.content || 'No preview available.';
  } catch (error) {
    console.error('❌ Error getting preview:', error);
    throw error;
  }
}

/**
 * Run AI analysis on a document
 */
export async function analyzeDocument(documentId) {
  if (!documentId) throw new Error('Document ID is required');
  try {
    const analysis = await request(ANALYSIS_API_URL, `/analyze`, {
      method: 'POST',
      body: JSON.stringify({ documentId, analysisType: 'full' }),
    });
    console.log('✅ Document analysis complete:', analysis);
    return analysis.data || analysis;
  } catch (error) {
    console.error('❌ Error analyzing document:', error);
    throw error;
  }
}


/**
 * Export analyzed results as PDF
 */
export async function exportAnalysisPDF(caseId) {
  const token = await getAuthToken();
  const res = await fetch(`${DOCUMENT_API_URL}/documents/${caseId}/export`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    throw new Error('❌ Failed to export analysis PDF');
  }

  return await res.blob();
}

/* ---------------------------------------------------------
 * 🧩 MOCK DATA BELOW (Optional fallback)
 * --------------------------------------------------------- */

const mockDelay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const mockDocuments = [
  {
    id: '1',
    filename: 'contract.pdf',
    caseId: '1',
    uploadedAt: new Date().toISOString(),
    pageCount: 5,
    size: 1024000,
  },
  {
    id: '2',
    filename: 'evidence.docx',
    caseId: '1',
    uploadedAt: new Date().toISOString(),
    pageCount: 3,
    size: 512000,
  },
];

export async function getMockDocuments(caseId) {
  await mockDelay(500);
  return mockDocuments.filter((doc) => doc.caseId === caseId);
}

export async function uploadMockDocument(file, caseId, userId) {
  await mockDelay(1000);
  const newDoc = {
    id: Date.now().toString(),
    filename: file.name,
    caseId,
    uploadedAt: new Date().toISOString(),
    pageCount: Math.floor(Math.random() * 10) + 1,
    size: file.size,
    uploadedBy: userId,
  };
  mockDocuments.push(newDoc);
  return newDoc;
}

export async function analyzeMockDocument(documentId) {
  await mockDelay(2000);
  const doc = mockDocuments.find((d) => d.id === documentId);
  return {
    summary: `AI analysis summary for ${doc?.filename || 'document'}`,
    keyPoints: [
      'Important clause identified in section 2.1',
      'Potential legal risk found in clause 4.3',
      'Standard boilerplate language detected',
    ],
    legalRelevance:
      'This document contains legally binding obligations and should be reviewed by legal counsel.',
  };
}

export async function getMockCaseAnalysis(caseId) {
  await mockDelay(1000);
  return {
    caseId,
    summary: 'Mock case analysis summary',
    recommendations: ['Review all contracts', 'Gather additional evidence'],
  };
}

export async function exportMockAnalysisPDF(caseId) {
  await mockDelay(1000);
  return new Blob(['Mock PDF content'], { type: 'application/pdf' });
}
