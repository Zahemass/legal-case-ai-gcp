import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './components/auth/Login';
import HomePage from './pages/HomePage';
import CasesPage from './pages/CasesPage';
import DocumentsPage from './pages/DocumentsPage';
import AIAgentPage from './pages/AIAgentPage';
import Navigation from './components/common/Navigation';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
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
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;