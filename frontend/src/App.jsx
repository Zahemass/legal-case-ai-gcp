import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./contexts/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";

import Login from "./components/auth/Login";
import HomePage from "./pages/HomePage";
import CasesPage from "./pages/CasesPage";
import DocumentsPage from "./pages/DocumentsPage";
import AIAgentPage from "./pages/AIAgentPage";
import CaseAnalysisView from "./components/analysis/CaseAnalysisView";

import AIAnalysisListPage from "./pages/AIAnalysisListPage";      // NEW
import AIAnalysisDetailsPage from "./pages/AIAnalysisDetailsPage"; // NEW

import Navigation from "./components/common/Navigation";
import "./App.css";

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">

          <Routes>

            {/* LOGIN PAGE */}
            <Route path="/login" element={<Login />} />

            {/* HOME PAGE */}
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

            {/* CASE MANAGEMENT */}
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

            {/* DOCUMENTS */}
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

            {/* AI CHAT AGENT */}
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

            <Route
  path="/analysis"
  element={
    <ProtectedRoute>
      <div className="d-flex">
        <Navigation />
        <div className="main-content flex-grow-1">
          <AIAnalysisListPage />
        </div>
      </div>
    </ProtectedRoute>
  }
/>

<Route
  path="/analysis/:analysisId"
  element={
    <ProtectedRoute>
      <div className="d-flex">
        <Navigation />
        <div className="main-content flex-grow-1">
          <AIAnalysisDetailsPage />
        </div>
      </div>
    </ProtectedRoute>
  }
/>


            {/* (Optional — your old CaseAnalysisView) */}
            <Route
              path="/case-analysis/:caseId"
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

            {/* FALLBACK */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>

        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
