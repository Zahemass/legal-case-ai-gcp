import React, { useState } from 'react';
import { Navbar, Nav, Container, Dropdown, Offcanvas, Button } from 'react-bootstrap';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import toast from 'react-hot-toast';
import './Navigation.css';

export default function Navigation() {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showOffcanvas, setShowOffcanvas] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Logged out successfully');
      navigate('/login');
    } catch (error) {
      console.error('Failed to logout:', error);
      toast.error('Failed to logout');
    }
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: 'bi-speedometer2' },
    { path: '/cases', label: 'Cases', icon: 'bi-briefcase' },
    { path: '/documents', label: 'Documents', icon: 'bi-file-earmark-text' },
  ];

  const isActive = (path) => {
    if (path === '/' && location.pathname === '/') return true;
    if (path !== '/' && location.pathname.startsWith(path)) return true;
    return false;
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <div className="sidebar d-none d-lg-flex">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <i className="bi bi-briefcase-fill"></i>
          </div>
          <h5 className="sidebar-title">Legal AI</h5>
        </div>

        <Nav className="sidebar-nav flex-column">
          {navItems.map((item) => (
            <Nav.Link 
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`sidebar-nav-link ${isActive(item.path) ? 'active' : ''}`}
            >
              <i className={`${item.icon} me-3`}></i>
              {item.label}
            </Nav.Link>
          ))}
        </Nav>

        <div className="sidebar-footer">
          <Dropdown drop="up">
            <Dropdown.Toggle 
              variant="light" 
              className="sidebar-user-btn w-100 d-flex align-items-center"
              id="dropdown-user"
            >
              <div className="user-avatar me-2">
                <i className="bi bi-person-fill"></i>
              </div>
              <div className="user-info flex-grow-1 text-start">
                <div className="user-name">{currentUser?.email?.split('@')[0]}</div>
                <div className="user-email">{currentUser?.email}</div>
              </div>
            </Dropdown.Toggle>

            <Dropdown.Menu className="sidebar-dropdown-menu">
              <Dropdown.Item onClick={() => navigate('/profile')}>
                <i className="bi bi-person me-2"></i>Profile
              </Dropdown.Item>
              <Dropdown.Item onClick={() => navigate('/settings')}>
                <i className="bi bi-gear me-2"></i>Settings
              </Dropdown.Item>
              <Dropdown.Divider />
              <Dropdown.Item onClick={handleLogout} className="text-danger">
                <i className="bi bi-box-arrow-right me-2"></i>Logout
              </Dropdown.Item>
            </Dropdown.Menu>
          </Dropdown>
        </div>
      </div>

      {/* Mobile Navbar */}
      <Navbar bg="white" className="mobile-navbar d-lg-none shadow-sm">
        <Container fluid>
          <Navbar.Brand className="d-flex align-items-center">
            <i className="bi bi-briefcase-fill text-primary me-2"></i>
            <span className="fw-bold">Legal AI</span>
          </Navbar.Brand>
          
          <Button 
            variant="outline-primary" 
            onClick={() => setShowOffcanvas(true)}
            className="mobile-menu-btn"
          >
            <i className="bi bi-list"></i>
          </Button>
        </Container>
      </Navbar>

      {/* Mobile Offcanvas */}
      <Offcanvas 
        show={showOffcanvas} 
        onHide={() => setShowOffcanvas(false)} 
        placement="start"
        className="mobile-offcanvas"
      >
        <Offcanvas.Header closeButton>
          <Offcanvas.Title>
            <div className="d-flex align-items-center">
              <i className="bi bi-briefcase-fill text-primary me-2"></i>
              Legal AI
            </div>
          </Offcanvas.Title>
        </Offcanvas.Header>
        
        <Offcanvas.Body>
          <Nav className="flex-column">
            {navItems.map((item) => (
              <Nav.Link 
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setShowOffcanvas(false);
                }}
                className={`mobile-nav-link ${isActive(item.path) ? 'active' : ''}`}
              >
                <i className={`${item.icon} me-3`}></i>
                {item.label}
              </Nav.Link>
            ))}
          </Nav>

          <div className="mobile-user-section mt-auto">
            <div className="user-info-mobile">
              <div className="user-avatar-mobile">
                <i className="bi bi-person-fill"></i>
              </div>
              <div>
                <div className="user-name-mobile">{currentUser?.email?.split('@')[0]}</div>
                <div className="user-email-mobile">{currentUser?.email}</div>
              </div>
            </div>
            
            <div className="d-grid gap-2 mt-3">
              <Button variant="outline-primary" size="sm" onClick={() => navigate('/profile')}>
                <i className="bi bi-person me-2"></i>Profile
              </Button>
              <Button variant="outline-secondary" size="sm" onClick={() => navigate('/settings')}>
                <i className="bi bi-gear me-2"></i>Settings
              </Button>
              <Button variant="outline-danger" size="sm" onClick={handleLogout}>
                <i className="bi bi-box-arrow-right me-2"></i>Logout
              </Button>
            </div>
          </div>
        </Offcanvas.Body>
      </Offcanvas>
    </>
  );
}