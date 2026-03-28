import './globals.css';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export const metadata = {
  title: 'Legal Case Similarity Search',
  description: 'Find similar legal cases using advanced NLP technology.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        <div id="app-content">
          {children}
        </div>
        <Footer />
      </body>
    </html>
  );
}
