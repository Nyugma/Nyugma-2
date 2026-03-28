import Link from 'next/link';

export default function Home() {
  return (
    <div className="home-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">Find Similar Legal Cases Instantly</h1>
          <p className="hero-description">
            Upload a legal document and discover similar cases using advanced Natural Language Processing technology. 
            Streamline your legal research with AI-powered document similarity analysis.
          </p>
          <Link href="/search" className="cta-button">
            <span>Get Started</span>
            <svg className="cta-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="5" y1="12" x2="19" y2="12"></line>
              <polyline points="12 5 19 12 12 19"></polyline>
            </svg>
          </Link>
        </div>
      </section>

      {/* About Section */}
      <section className="about-section">
        <div className="section-container">
          <h2 className="section-title">About</h2>
          <div className="about-content">
            <p className="about-text">
              The Nyugma Legal Case Similarity Search application is a powerful tool designed to help legal professionals, 
              researchers, and students quickly find relevant case law. By leveraging state-of-the-art Natural Language 
              Processing (NLP) and machine learning techniques, our system analyzes the content of legal documents and 
              identifies cases with similar legal issues, arguments, and precedents.
            </p>
            <p className="about-text">
              Our application processes PDF documents, extracts meaningful legal text, and compares it against a 
              comprehensive database of legal cases. The similarity scoring system ranks results by relevance, 
              helping you find the most pertinent cases for your research or case preparation in seconds rather than hours.
            </p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="section-container">
          <h2 className="section-title">Features</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
              </div>
              <h3 className="feature-title">PDF Processing</h3>
              <p className="feature-description">
                Upload legal documents in PDF format. Our system automatically extracts and analyzes text content 
                with support for files up to 10MB.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
              </div>
              <h3 className="feature-title">Intelligent Search</h3>
              <p className="feature-description">
                Advanced NLP algorithms analyze document content and identify similar cases based on legal concepts, 
                arguments, and precedents.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </div>
              <h3 className="feature-title">Similarity Scoring</h3>
              <p className="feature-description">
                Results are ranked by relevance with percentage-based similarity scores, helping you quickly identify 
                the most relevant cases.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
              </div>
              <h3 className="feature-title">Case Download</h3>
              <p className="feature-description">
                Download full case documents directly from the results page for detailed review and citation in your work.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
              </div>
              <h3 className="feature-title">Secure Processing</h3>
              <p className="feature-description">
                Your documents are processed securely with industry-standard encryption. Uploaded files are not stored 
                permanently on our servers.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                  <line x1="8" y1="21" x2="16" y2="21"></line>
                  <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
              </div>
              <h3 className="feature-title">Responsive Design</h3>
              <p className="feature-description">
                Access the application from any device - desktop, tablet, or mobile. Our responsive interface adapts 
                to your screen size.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How to Use Section */}
      <section className="how-to-use-section" style={{marginBottom: "60px"}}>
        <div className="section-container">
          <h2 className="section-title">How to Use</h2>
          <div className="steps-container">
            <div className="step-item">
              <div className="step-number-badge">1</div>
              <div className="step-content">
                <h3 className="step-title">Upload Your Document</h3>
                <p className="step-description">
                  Navigate to the Search page and upload your legal document in PDF format. You can drag and drop 
                  the file or click to browse. Maximum file size is 10MB.
                </p>
              </div>
            </div>

            <div className="step-item">
              <div className="step-number-badge">2</div>
              <div className="step-content">
                <h3 className="step-title">Wait for Analysis</h3>
                <p className="step-description">
                  Our system will extract text from your PDF, preprocess the content, and analyze it using advanced 
                  NLP algorithms. This typically takes 10-30 seconds depending on document size.
                </p>
              </div>
            </div>

            <div className="step-item">
              <div className="step-number-badge">3</div>
              <div className="step-content">
                <h3 className="step-title">Review Similar Cases</h3>
                <p className="step-description">
                  Browse through the results ranked by similarity score. Each result includes the case title, date, 
                  a relevant excerpt, and the similarity percentage.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
