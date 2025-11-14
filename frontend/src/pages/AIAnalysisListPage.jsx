// src/pages/AIAnalysisListPage.jsx
import React, { useEffect, useState } from "react";
import { collection, getDocs, doc, getDoc } from "firebase/firestore";
import { db } from "../firebase";
import { useNavigate } from "react-router-dom";
import { 
  Scale, 
  FileText, 
  Calendar, 
  Search,
  Filter,
  ArrowRight,
  Clock,
  Briefcase,
  TrendingUp,
  BarChart3,
  FolderOpen
} from "lucide-react";
import "./AIAnalysisListPage.css";

export default function AIAnalysisListPage() {
  const [latestAnalyses, setLatestAnalyses] = useState([]);
  const [filteredAnalyses, setFilteredAnalyses] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const loadAnalyses = async () => {
      try {
        setLoading(true);
        const colRef = collection(db, "case_analyses");
        const snapshot = await getDocs(colRef);

        const all = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data(),
        }));

        // Group by caseId → select latest analyzedAt
        const grouped = {};

        all.forEach(item => {
          const caseId = item.caseId;
          if (!caseId) return;

          const existing = grouped[caseId];

          if (!existing) {
            grouped[caseId] = item;
          } else {
            const oldTime = new Date(existing.analyzedAt).getTime();
            const newTime = new Date(item.analyzedAt).getTime();
            if (newTime > oldTime) {
              grouped[caseId] = item;
            }
          }
        });

        const latest = Object.values(grouped);

        // Fetch case details
        const withCaseData = await Promise.all(
          latest.map(async analysis => {
            try {
              const caseRef = doc(db, "cases", analysis.caseId);
              const caseSnap = await getDoc(caseRef);

              if (caseSnap.exists()) {
                const caseData = caseSnap.data();

                return {
                  ...analysis,
                  caseTitle: caseData.title || "Untitled Case",
                  caseType: caseData.type || "unknown",
                };
              } else {
                return {
                  ...analysis,
                  caseTitle: "Unknown Case",
                  caseType: "unknown",
                };
              }
            } catch (e) {
              console.log("Case fetch error:", e);
              return analysis;
            }
          })
        );

        const filtered = withCaseData.filter(a => a.caseTitle !== "Unknown Case");
        setLatestAnalyses(filtered);
        setFilteredAnalyses(filtered);
      } catch (err) {
        console.error("Error fetching analyses:", err);
      } finally {
        setLoading(false);
      }
    };

    loadAnalyses();
  }, []);

  // Filter and search logic
  useEffect(() => {
    let result = [...latestAnalyses];

    if (selectedType !== "all") {
      result = result.filter(a => a.caseType?.toLowerCase() === selectedType.toLowerCase());
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(a => 
        a.caseTitle?.toLowerCase().includes(query) ||
        a.executiveSummary?.toLowerCase().includes(query)
      );
    }

    setFilteredAnalyses(result);
  }, [searchQuery, selectedType, latestAnalyses]);

  const getCaseTypeColor = (type) => {
    const colors = {
      criminal: "#DC2626",
      civil: "#2563EB",
      corporate: "#7C3AED",
      family: "#DB2777",
      property: "#059669",
      constitutional: "#D97706",
      labor: "#0891B2",
    };
    return colors[type?.toLowerCase()] || "#6B7280";
  };

  const getCaseTypeIcon = (type) => {
    switch(type?.toLowerCase()) {
      case 'criminal': return '⚖️';
      case 'civil': return '📋';
      case 'corporate': return '🏢';
      case 'family': return '👨‍👩‍👧';
      case 'property': return '🏠';
      case 'constitutional': return '📜';
      case 'labor': return '👷';
      default: return '📁';
    }
  };

  const getCaseTypes = () => {
    const types = new Set(latestAnalyses.map(a => a.caseType));
    return ["all", ...Array.from(types)];
  };

  const getStats = () => {
    const totalDocs = latestAnalyses.reduce((sum, a) => 
      sum + (a.totalDocuments || a.documentCount || 0), 0);
    const avgDocs = latestAnalyses.length ? (totalDocs / latestAnalyses.length).toFixed(1) : 0;
    
    return {
      total: latestAnalyses.length,
      totalDocs,
      avgDocs
    };
  };

  const stats = getStats();

  return (
    <div className="analysis-page-container">
      {/* Top Navigation Bar */}
      <div className="top-nav">
        <div className="nav-content">
          <div className="logo-section">
            <div className="logo-icon">
              <Scale size={24} strokeWidth={2.5} />
            </div>
            <span className="logo-text">LegalAI</span>
          </div>
          
          <nav className="nav-links">
            <a href="/dashboard" className="nav-link">
              <BarChart3 size={18} />
              Dashboard
            </a>
            <a href="/cases" className="nav-link">
              <FolderOpen size={18} />
              Cases
            </a>
            <a href="/analysis" className="nav-link active">
              <Briefcase size={18} />
              AI Analysis
            </a>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Hero Section */}
        <div className="hero-section">
          <div className="hero-text">
            <h1 className="hero-title">AI Case Analyses</h1>
            <p className="hero-subtitle">
              Comprehensive legal analysis powered by advanced artificial intelligence
            </p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon" style={{background: '#EEF2FF'}}>
              <Briefcase size={24} color="#4F46E5" />
            </div>
            <div className="stat-info">
              <p className="stat-value">{stats.total}</p>
              <p className="stat-label">Total Cases</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{background: '#FEF3C7'}}>
              <FileText size={24} color="#D97706" />
            </div>
            <div className="stat-info">
              <p className="stat-value">{stats.totalDocs}</p>
              <p className="stat-label">Documents Analyzed</p>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon" style={{background: '#D1FAE5'}}>
              <TrendingUp size={24} color="#059669" />
            </div>
            <div className="stat-info">
              <p className="stat-value">{stats.avgDocs}</p>
              <p className="stat-label">Avg. Docs/Case</p>
            </div>
          </div>
        </div>

        {/* Controls Section */}
        <div className="controls-section">
          <div className="search-wrapper">
            <Search size={20} className="search-icon" />
            <input
              type="text"
              placeholder="Search cases by title or summary..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="filter-wrapper">
            <Filter size={18} className="filter-icon" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="filter-select"
            >
              {getCaseTypes().map(type => (
                <option key={type} value={type}>
                  {type === "all" ? "All Case Types" : type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Loading State */}
        {loading ? (
          <div className="loading-state">
            <div className="loader"></div>
            <p className="loading-text">Loading analyses...</p>
          </div>
        ) : (
          <>
            {/* Results Info */}
            <div className="results-info">
              <p className="results-text">
                Showing <strong>{filteredAnalyses.length}</strong> of <strong>{latestAnalyses.length}</strong> cases
              </p>
            </div>

            {/* Cases Grid */}
            <div className="cases-grid">
              {filteredAnalyses.map(item => (
                <div
                  key={item.id}
                  className="case-card"
                  onClick={() => navigate(`/analysis/${item.id}`)}
                >
                  {/* Card Top */}
                  <div className="card-top">
                    <div 
                      className="case-badge"
                      style={{
                        background: `${getCaseTypeColor(item.caseType)}15`,
                        color: getCaseTypeColor(item.caseType)
                      }}
                    >
                      <span className="badge-emoji">{getCaseTypeIcon(item.caseType)}</span>
                      <span className="badge-text">{item.caseType?.toUpperCase()}</span>
                    </div>
                    <ArrowRight className="card-arrow" size={20} />
                  </div>

                  {/* Case Title */}
                  <h3 className="case-title">{item.caseTitle}</h3>

                  {/* Summary */}
                  <p className="case-summary">
                    {item.executiveSummary
                      ? item.executiveSummary.substring(0, 140) + "..."
                      : "No summary available for this case"}
                  </p>

                  {/* Card Meta */}
                  <div className="card-meta-section">
                    <div className="meta-item">
                      <Calendar size={16} />
                     
                    </div>

                    <div className="meta-divider"></div>

                    <div className="meta-item">
                      <FileText size={16} />
                      <span>{item.totalDocuments || item.documentCount || 0} Documents</span>
                    </div>
                  </div>

                  {/* View Button */}
                  <button className="view-button">
                    <span>View Full Analysis</span>
                    <ArrowRight size={18} />
                  </button>
                </div>
              ))}
            </div>

            {/* Empty State */}
            {filteredAnalyses.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">
                  <Search size={48} strokeWidth={1.5} />
                </div>
                <h3 className="empty-title">No cases found</h3>
                <p className="empty-text">
                  Try adjusting your search or filter to find what you're looking for
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
