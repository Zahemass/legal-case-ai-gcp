import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './components/auth/Login';
import HomePage from './pages/HomePage';
import CasesPage from './pages/CasesPage';
import DocumentsPage from './pages/DocumentsPage';
import AIAgentPage from './pages/AIAgentPage';
import CaseAnalysisView from './components/analysis/CaseAnalysisView';
import Navigation from './components/common/Navigation';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* 🔐 Login Page */}
            <Route path="/login" element={<Login />} />

            {/* 🏠 Home Page */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <div className="d-flex">
                    <Navigation />
                    <div className="main-content flex-grow-1">
                      <HomePage />
                    </div>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* 📁 Cases Page */}
            <Route
              path="/cases"
              element={
                <ProtectedRoute>
                  <div className="d-flex">
                    <Navigation />
                    <div className="main-content flex-grow-1">
                      <CasesPage />
                    </div>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* 📄 Documents Page */}
            <Route
              path="/documents"
              element={
                <ProtectedRoute>
                  <div className="d-flex">
                    <Navigation />
                    <div className="main-content flex-grow-1">
                      <DocumentsPage />
                    </div>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* 🤖 AI Agent Page */}
            <Route
              path="/ai-agent/:caseId"
              element={
                <ProtectedRoute>
                  <div className="d-flex">
                    <Navigation />
                    <div className="main-content flex-grow-1">
                      <AIAgentPage />
                    </div>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* 🧠 AI Case Analysis Page */}
            <Route
              path="/analysis/:caseId"
              element={
                <ProtectedRoute>
                  <div className="d-flex">
                    <Navigation />
                    <div className="main-content flex-grow-1">
                      <CaseAnalysisView />
                    </div>
                  </div>
                </ProtectedRoute>
              }
            />

            {/* 🚧 Fallback Route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
