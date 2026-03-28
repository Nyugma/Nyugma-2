'use client';

import { useState } from 'react';

export default function SearchPage() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setResults(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${url}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.message || 'An error occurred during search.');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="container">
      <header className="header">
        <h1 className="title">Legal Case Similarity Search</h1>
        <p className="subtitle">Upload a legal document to find similar cases in our database</p>
      </header>

      <main className="main-content">
        <section className="upload-section">
          <div className="upload-container">
            {!loading && !results && !error && (
              <form id="uploadForm" className="upload-form" onSubmit={handleSearch}>
                <div className="file-input-container">
                  <input
                    type="file"
                    id="fileInput"
                    name="file"
                    accept=".pdf"
                    required
                    className="file-input"
                    onChange={handleFileChange}
                  />
                  <label htmlFor="fileInput" className="file-input-label">
                    <div className="file-input-content">
                      <svg className="upload-icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7,10 12,15 17,10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                      </svg>
                      <span className="file-input-text">Choose PDF file or drag and drop</span>
                      <span className="file-input-subtext">Maximum file size: 10MB</span>
                    </div>
                  </label>
                </div>

                {file && (
                  <div className="selected-file">
                    <div className="file-info">
                      <svg className="file-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"></path>
                      </svg>
                      <span className="file-name">{file.name}</span>
                      <span className="file-size">{formatFileSize(file.size)}</span>
                    </div>
                    <button type="button" className="remove-file" onClick={() => setFile(null)}>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                )}

                <button type="submit" className="submit-button" disabled={!file}>
                  <span className="button-text">Search Similar Cases</span>
                </button>
              </form>
            )}

            {loading && (
              <div className="loading-container">
                <div className="loading-spinner"></div>
                <div className="loading-text">
                  <h3>Processing Document...</h3>
                  <p>Analyzing your document and searching for similar cases</p>
                </div>
              </div>
            )}
          </div>
        </section>

        {results && results.results && results.results.length > 0 && (
          <section className="results-section">
            <div className="results-header">
              <h2 className="results-title">Similar Cases Found</h2>
              <div className="results-meta">
                Found {results.results.length} cases in {results.processing_time.toFixed(2)}s
              </div>
            </div>
            <div className="results-container">
              {results.results.map((item, idx) => (
                <div key={idx} className="case-result fade-in" style={{ animationDelay: `${idx * 0.1}s` }}>
                  <div className="case-header">
                    <div className="case-info">
                      <h3 className="case-title">{item.title}</h3>
                      <div className="case-meta">
                        <span className="case-date">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                            <line x1="16" y1="2" x2="16" y2="6"></line>
                            <line x1="8" y1="2" x2="8" y2="6"></line>
                            <line x1="3" y1="10" x2="21" y2="10"></line>
                          </svg>
                          {new Date(item.date).toLocaleDateString()}
                        </span>
                        <span className="similarity-score">
                          <span className="similarity-badge">{Math.round(item.similarity_score * 100)}% Match</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  <p className="case-snippet">"{item.snippet}"</p>
                  <div className="case-actions">
                    <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${item.download_url}`} target="_blank" rel="noopener noreferrer" className="download-button">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                      </svg>
                      Download PDF
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {results && results.results && results.results.length === 0 && (
          <section className="empty-results-section">
            <div className="empty-results-container">
              <div className="empty-results-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
              </div>
              <h3 className="empty-results-title">No Similar Cases Found</h3>
              <p className="empty-results-message">We couldn't find any cases similar to your document.</p>
              <button className="upload-another-button" onClick={() => setResults(null)}>Upload Another Document</button>
            </div>
          </section>
        )}

        {error && (
          <section className="error-section">
            <div className="error-container">
              <div className="error-icon">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="15" y1="9" x2="9" y2="15"></line>
                  <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
              </div>
              <h3 className="error-title">Something went wrong</h3>
              <p className="error-message">{error}</p>
              <button className="retry-button" onClick={() => setError(null)}>Try Again</button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
