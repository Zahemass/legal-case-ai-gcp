import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Tabs, Tab } from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [activeTab, setActiveTab] = useState('login');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, signup } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();

    if (activeTab === 'signup' && password !== confirmPassword) {
      return setError('Passwords do not match');
    }

    try {
      setError('');
      setLoading(true);
      
      if (activeTab === 'login') {
        await login(email, password);
        toast.success('Welcome back!');
      } else {
        await signup(email, password);
        toast.success('Account created successfully!');
      }
      
      navigate('/');
    } catch (error) {
      console.error('Auth error:', error);
      setError('Authentication failed. Please try again.');
      toast.error('Authentication failed');
    }
    setLoading(false);
  }

  return (
    <div className="login-page">
      <Container>
        <Row className="justify-content-center align-items-center min-vh-100">
          <Col md={6} lg={5} xl={4}>
            <div className="login-container animate-fade-in">
              <div className="text-center mb-4">
                <div className="login-logo">
                  <i className="bi bi-briefcase-fill"></i>
                </div>
                <h2 className="login-title">Legal Case AI</h2>
                <p className="login-subtitle">Intelligent Legal Case Management</p>
              </div>

              <Card className="login-card">
                <Card.Body className="p-4">
                  <Tabs
                    activeKey={activeTab}
                    onSelect={(k) => {
                      setActiveTab(k);
                      setError('');
                      setEmail('');
                      setPassword('');
                      setConfirmPassword('');
                    }}
                    className="nav-tabs-custom mb-4"
                  >
                    <Tab eventKey="login" title="Log In">
                      <Form onSubmit={handleSubmit}>
                        {error && <Alert variant="danger" className="mb-3">{error}</Alert>}
                        
                        <Form.Group className="mb-3">
                          <Form.Label>Email Address</Form.Label>
                          <Form.Control
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            placeholder="Enter your email"
                            className="form-control-custom"
                          />
                        </Form.Group>

                        <Form.Group className="mb-4">
                          <Form.Label>Password</Form.Label>
                          <Form.Control
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            placeholder="Enter your password"
                            className="form-control-custom"
                          />
                        </Form.Group>

                        <Button
                          type="submit"
                          variant="primary"
                          className="w-100 btn-custom"
                          disabled={loading}
                        >
                          {loading ? (
                            <>
                              <span className="spinner me-2"></span>
                              Logging In...
                            </>
                          ) : (
                            <>

                              Log In
                            </>
                          )}
                        </Button>
                      </Form>
                    </Tab>

                    <Tab eventKey="signup" title="Sign Up">
                      <Form onSubmit={handleSubmit}>
                        {error && <Alert variant="danger" className="mb-3">{error}</Alert>}
                        
                        <Form.Group className="mb-3">
                          <Form.Label>Email Address</Form.Label>
                          <Form.Control
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            placeholder="Enter your email"
                            className="form-control-custom"
                          />
                        </Form.Group>

                        <Form.Group className="mb-3">
                          <Form.Label>Password</Form.Label>
                          <Form.Control
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            placeholder="Create a password"
                            className="form-control-custom"
                            minLength={6}
                          />
                        </Form.Group>

                        <Form.Group className="mb-4">
                          <Form.Label>Confirm Password</Form.Label>
                          <Form.Control
                            type="password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            placeholder="Confirm your password"
                            className="form-control-custom"
                            minLength={6}
                          />
                        </Form.Group>

                        <Button
                          type="submit"
                          variant="primary"
                          className="w-100 btn-custom"
                          disabled={loading}
                        >
                          {loading ? (
                            <>
                              <span className="spinner me-2"></span>
                              Creating Account...
                            </>
                          ) : (
                            <>
                              <i className="bi bi-person-plus me-2"></i>
                              Create Account
                            </>
                          )}
                        </Button>
                      </Form>
                    </Tab>
                  </Tabs>
                </Card.Body>
              </Card>

              <div className="login-footer">
                <p className="text-center text-muted">
                  © 2025 Legal Case AI for GCP Run Cloud Hackathon. All rights reserved.
                </p>
              </div>
            </div>
          </Col>
        </Row>
      </Container>
    </div>
  );
}