// frontend/services/api.js
import { auth } from '../firebase';

/* ---------------------------------------------------------
 * ⚙️ Firebase Auth Helpers for Cloud Run + Local backend
 * --------------------------------------------------------- */
const CASE_API_URL = import.meta.env.VITE_CASE_API_URL || 'http://localhost:8080';
const DOCUMENT_API_URL = import.meta.env.VITE_DOCUMENT_API_URL || 'http://localhost:8080';
const ANALYSIS_API_URL = import.meta.env.VITE_ANALYSIS_API_URL || 'http://localhost:8080';
const VITE_CASE_ANALYSIS_API_URL = import.meta.env.VITE_CASE_ANALYSIS_API_URL || 'http://localhost:8080';
const AI_AGENT_API_URL = import.meta.env.VITE_AI_AGENT_API_URL || 'http://localhost:8080';



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
    const response = await request(CASE_API_URL, '/cases', { method: 'GET' });

    const cases = Array.isArray(response?.data?.cases)
      ? response.data.cases
      : Array.isArray(response?.cases)
      ? response.cases
      : [];

    console.log("🧾 Raw API cases:", cases);

    const normalized = cases.map((c) => {
      const documentCount =
        typeof c.documentCount === 'number'
          ? c.documentCount
          : typeof c.document_count === 'number'
          ? c.document_count
          : (c?.data?.documentCount ?? 0);

      const analysisCount =
        typeof c.analysisCount === 'number'
          ? c.analysisCount
          : typeof c.analysis_count === 'number'
          ? c.analysis_count
          : (c?.data?.analysisCount ?? 0);

      return {
        ...c,
        documentCount,
        analysisCount,
        title: c.title ?? 'Untitled Case',
        status: c.status ?? 'active',
        priority: c.priority ?? 'medium',
        type: c.type ?? 'other',
      };
    });

    console.log("📂 Normalized cases:", normalized);

    return {
      success: true,
      data: { cases: normalized },
    };
  } catch (err) {
    console.error('❌ Error fetching cases:', err);
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
 * 🧠 CASE ANALYSIS SERVICE (Cloud Run: case-analysis-service)
 * --------------------------------------------------------- */

/**
 * Fetch or trigger AI analysis directly from the Case Analysis Service.
 */
export async function getCaseAnalysis(caseId) {
  if (!caseId) throw new Error('Case ID is required');

  try {
    const response = await request(VITE_CASE_ANALYSIS_API_URL, `/analyze`, {
      method: 'POST',
      body: JSON.stringify({ caseId, analysisType: 'comprehensive' }),
    });

    console.log('✅ Case analysis retrieved successfully:', response);
    return response.data || response;
  } catch (error) {
    console.error('❌ Error fetching case analysis from Case Analysis Service:', error);
    throw error;
  }
}

/* ---------------------------------------------------------
 * 📄 DOCUMENT MANAGEMENT (Local: document-service)
 * --------------------------------------------------------- */

/**
 * Get all documents for a specific case
 */
export async function getDocuments(caseId) {
  if (!caseId) throw new Error('Case ID is required');
  try {
    const response = await request(DOCUMENT_API_URL, `/documents?caseId=${caseId}`, {
      method: 'GET',
    });

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
    const preview = await request(
      DOCUMENT_API_URL,
      `/documents/${documentId}/preview`,
      { method: 'GET' }
    );

    console.log('✅ Preview loaded:', preview);

    const content =
      preview?.data?.textPreview?.content ||
      preview?.data?.content ||
      preview?.content ||
      preview?.summary ||
      'No preview available.';

    return content;
  } catch (error) {
    console.error('❌ Error getting preview:', error);
    return 'No preview available.';
  }
}

/**
 * Run AI analysis on a document
 */
export async function analyzeDocument(documentId) {
  if (!documentId) throw new Error('Document ID is required');
  try {
    const token = await getAuthToken();

    const res = await fetch(`${ANALYSIS_API_URL}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ documentId, analysisType: 'full' }),
    });

    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      console.warn('⚠️ Non-JSON response received from /analyze:', text);
      throw new Error('Invalid response from AI analysis service');
    }

    if (!res.ok) {
      console.error('❌ API Error in analyzeDocument:', data);
      throw new Error(data?.error || 'AI Analysis failed');
    }

    const cleaned = JSON.parse(
      JSON.stringify(data, (_k, v) => {
        if (
          v &&
          typeof v === 'object' &&
          (v._seconds || v._nanoseconds || v.protobuf || v.timestamp)
        ) {
          return null;
        }
        return v;
      })
    );

    console.log('✅ Document analysis complete:', cleaned);
    return cleaned.data || cleaned;
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
 * 🤖 AI AGENT SERVICE (REST API: ai-agent-service)
 * --------------------------------------------------------- */

/**
 * Send message to AI Agent and get response
 */
export async function sendAIMessage(caseId, userId, message) {
  if (!caseId || !userId || !message) {
    throw new Error('caseId, userId, and message are required');
  }

  try {
    console.log('📤 Sending AI message:', { caseId, userId, message: message.substring(0, 50) });
    
    const response = await fetch(`${AI_AGENT_API_URL}/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        caseId,
        userId,
        message,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to send message');
    }

    const data = await response.json();
    console.log('✅ AI response received:', data);
    return data;
  } catch (error) {
    console.error('❌ Error sending AI message:', error);
    throw error;
  }
}

/**
 * Get chat history for a case
 */
export async function getAIChatHistory(caseId) {
  if (!caseId) throw new Error('Case ID is required');

  try {
    console.log('📚 Fetching chat history for case:', caseId);
    
    const response = await fetch(`${AI_AGENT_API_URL}/chat/history/${caseId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to fetch chat history');
    }

    const data = await response.json();
    console.log('✅ Chat history loaded:', data);
    return data;
  } catch (error) {
    console.error('❌ Error fetching chat history:', error);
    return { success: false, messages: [] };
  }
}

/**
 * Get list of available AI agents
 */
export async function getAIAgents() {
  try {
    const response = await request(AI_AGENT_API_URL, '/agents', { method: 'GET' });
    console.log('✅ AI Agents fetched:', response.agents);
    return response.agents || [];
  } catch (error) {
    console.error('❌ Error fetching AI agents:', error);
    return [];
  }
}

/**
 * Health check for AI Agent Service
 */
export async function getAIAgentHealth() {
  try {
    const response = await fetch(`${AI_AGENT_API_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    console.log('✅ AI Agent Service is healthy:', data);
    return data;
  } catch (error) {
    console.error('❌ AI Agent Service is not reachable:', error);
    throw error;
  }
}

/* ---------------------------------------------------------
 * 🧩 MOCK DATA (Optional fallback)
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
