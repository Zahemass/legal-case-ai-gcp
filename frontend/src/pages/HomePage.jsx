import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Container, Row, Col } from 'react-bootstrap';
import './HomePage.css';

export default function HomePage() {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Failed to logout:', error);
    }
  };

  return (
    <div className="home-container">
      
      {/* HEADER */}
      <div className="header">
        <Container>
          <h1>Legal Case AI System</h1>
          <div className="user-info">
            <span>Welcome, {currentUser?.email}</span>
            <button onClick={handleLogout} className="logout-btn">Logout</button>
          </div>
        </Container>
      </div>
      
      {/* MAIN CARDS */}
      <main className="main-content">
        <Container>
          <Row className="dashboard-grid">

            <Col lg={3} md={6} className="mb-4">
              <div className="dashboard-card" onClick={() => navigate('/cases')}>
                <div className="card-icon">📋</div>
                <h3>Case Management</h3>
                <p>View and manage all your legal cases</p>
              </div>
            </Col>

            <Col lg={3} md={6} className="mb-4">
              <div className="dashboard-card" onClick={() => navigate('/documents')}>
                <div className="card-icon">📄</div>
                <h3>Document Library</h3>
                <p>Upload and organize case documents</p>
              </div>
            </Col>

            <Col lg={3} md={6} className="mb-4">
              <div 
                className="dashboard-card" 
                onClick={() => navigate('/analysis')}
              >
                <div className="card-icon">🤖</div>
                <h3>AI Analysis</h3>
                <p>View all AI-powered insights</p>
              </div>
            </Col>

            <Col lg={3} md={6} className="mb-4">
              <div className="dashboard-card">
                <div className="card-icon">📊</div>
                <h3>Reports</h3>
                <p>Generate comprehensive case reports</p>
              </div>
            </Col>

          </Row>
        </Container>
      </main>

    </div>
  );
}
