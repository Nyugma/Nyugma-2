"""
Ingest the platform Q&A knowledge base into ChromaDB.

Run from the backend directory:
    python scripts/ingest_knowledge_base.py
"""

import sys
from pathlib import Path

# Add parent to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import chromadb

PERSIST_DIR = str(Path(__file__).parent.parent / "data" / "chromadb")

# Platform Q&A knowledge base
KNOWLEDGE_BASE = [
    {
        "id": "qa-01",
        "question": "What is the Legal Case Similarity platform?",
        "answer": "The Legal Case Similarity platform is a specialized web application designed to connect users through legal document analysis. It utilizes document similarity analysis to help users find legal cases that are factually and contextually similar to their own. The platform serves as a bridge, connecting New Litigants (individuals starting a legal case) with Helpers (individuals who have previously navigated similar legal situations). It aims to democratize legal knowledge by allowing experienced individuals to share their insights, providing moral support and practical guidance to newcomers. The backend employs Natural Language Processing (NLP) and machine learning algorithms to compare the content of legal documents.",
    },
    {
        "id": "qa-02",
        "question": "How do I register on the platform?",
        "answer": "Registration is a straightforward process. Click on the Login link in the navigation bar, then select the Register tab. You will be asked to select your role: New Litigant or Helper. Fill in all mandatory fields including a valid email address, a secure password, and your full name. Then click the Register button to create your account.",
    },
    {
        "id": "qa-03",
        "question": "What's the difference between a New Litigant and Helper?",
        "answer": "New Litigants seek assistance, information, and guidance for a legal case they are currently involved in. They can upload their own legal documents to find similar past cases and connect with relevant Helpers. Helpers offer assistance based on their past legal experiences, acting as mentors or guides. They can upload their resolved case documents to the database via Add Case, be discovered by New Litigants whose cases are similar, and have a dashboard to manage their contributed cases and messages.",
    },
    {
        "id": "qa-04",
        "question": "Where can I upload my legal documents?",
        "answer": "New Litigants have a dedicated page for uploading documents and initiating similarity searches. Navigate to the Search page by clicking on the Search link in the main navigation menu. Once on the Search page, locate the file upload area, which is clearly marked. Click the upload button or drag and drop your PDF file into the designated area. The system will then process the file to perform the similarity search.",
    },
    {
        "id": "qa-05",
        "question": "What file formats are supported for document upload?",
        "answer": "The platform currently supports only PDF (Portable Document Format) files. Ensure any legal documents, whether they are petitions, judgments, or affidavits, are saved or converted to a standard PDF format before uploading.",
    },
    {
        "id": "qa-06",
        "question": "How does the case similarity search work?",
        "answer": "When a New Litigant uploads a PDF, the system first extracts all the raw text content. Advanced NLP techniques are applied to understand the context and identify key legal concepts. The text is converted into a numerical vector using TF-IDF, creating a unique fingerprint for the case. This vector is compared against vectors of all cases in the database using cosine similarity. Cases are ranked based on their similarity score, and the highest-scoring cases are returned as search results.",
    },
    {
        "id": "qa-07",
        "question": "How do I become a Helper on the platform?",
        "answer": "Becoming a Helper is part of the initial registration process. When registering for a new account, select Helper from the user type choices. Complete the registration form with your full name, email address, and a password. You can optionally provide your phone number, city, and state. Once registered, your dashboard and permissions will be configured for the Helper role.",
    },
    {
        "id": "qa-08",
        "question": "Where can Helpers add their case experiences?",
        "answer": "After logging in as a Helper, click on the Add Case link in the navigation menu. This takes you to the Helper dashboard, which is specifically designed for managing and adding new cases. There is a form to fill out with details about the case and an option to upload the corresponding PDF documents.",
    },
    {
        "id": "qa-09",
        "question": "What information do I need to provide as a Helper?",
        "answer": "During registration you must provide your full name, email, and password. Optionally you can add phone number, city, state, and a short bio. When adding a case, you must upload the relevant PDF documents and may be asked to provide case title, year, court name, or a brief summary.",
    },
    {
        "id": "qa-10",
        "question": "How can I contact other users on the platform?",
        "answer": "The platform includes a built-in messaging system, eliminating the need to share personal contact information publicly. A New Litigant and a Helper can start communicating once they are connected through a similar case. All conversations are accessible through a dedicated Messages or Inbox section on the user's dashboard.",
    },
    {
        "id": "qa-11",
        "question": "Is my personal information secure on the platform?",
        "answer": "Yes, the platform employs several industry-standard security measures. Passwords are securely hashed using a strong one-way cryptographic algorithm. The platform uses JSON Web Tokens (JWT) for secure authentication. All personal information and case documents are stored in a secure database with controlled access.",
    },
    {
        "id": "qa-12",
        "question": "Can I update my profile information after registration?",
        "answer": "Yes, users have full control over their profile information. Navigate to your user profile settings, usually found by clicking on your username or avatar icon. You can update your full name, phone number, city, state, and bio. Click Save or Update Profile to apply changes. Email addresses are often not changeable for security reasons.",
    },
    {
        "id": "qa-13",
        "question": "How do I log in to my account?",
        "answer": "Click on the Login link in the navigation bar at the top of the page. Enter the email address and password you used during registration. Click the Login button. If credentials are correct, you will be logged in and redirected to your personalized dashboard.",
    },
    {
        "id": "qa-14",
        "question": "What should I do if I forget my password?",
        "answer": "There is currently no automated Forgot Password feature. If you forget your password, contact the platform's support team or system administrator for assistance. Look for a Contact Us or Support link in the website footer. A self-service password reset feature is planned for a future update.",
    },
    {
        "id": "qa-15",
        "question": "How can I view my dashboard?",
        "answer": "Upon successfully logging in, you are automatically taken to your user dashboard. If you navigate away, you can return via the Dashboard link in the main navigation menu. The content of your dashboard differs based on your role - Helpers see their case contributions, while Litigants see their search history.",
    },
    {
        "id": "qa-16",
        "question": "What types of legal cases can I search for?",
        "answer": "The platform is domain-agnostic and can handle a wide variety of legal texts. The similarity search is not limited to a specific legal domain like criminal, civil, or family law. The system analyzes the actual content and legal terminology within the uploaded document. The breadth of results is limited only by the diversity and number of cases uploaded by Helpers.",
    },
    {
        "id": "qa-17",
        "question": "How accurate is the case similarity matching?",
        "answer": "The matching engine relies on TF-IDF vectorization which weighs the importance of words against how common they are across all documents. It uses cosine similarity to measure similarity between document vectors. This combination is highly effective for comparing legal documents, accurately finding cases that share specific terminology, cited laws, and factual patterns.",
    },
    {
        "id": "qa-18",
        "question": "Can I download similar cases found by the system?",
        "answer": "Yes. When search results are displayed, each listed case will have a Download button or link. Clicking this initiates a download of the original PDF document for that similar case, allowing you to save it for detailed offline reading and analysis.",
    },
    {
        "id": "qa-19",
        "question": "How do I navigate to the main search functionality?",
        "answer": "Look at the top of the webpage for the primary navigation bar. Click directly on the Search link within this menu. This takes you to the dedicated Search page where you will find the document upload area and tools needed to perform a similarity search.",
    },
    {
        "id": "qa-20",
        "question": "What details are shown in search results?",
        "answer": "Search results show: Case Title, Date of the judgment or filing, Similarity Score indicating how closely the case aligns with your document, a Content Snippet showing context of the match, and a Download Link to get the full PDF document.",
    },
    {
        "id": "qa-21",
        "question": "How can I check if the system is working properly?",
        "answer": "If the platform is working properly, pages will load, you can log in, and uploads will process successfully. Error messages will appear if something is wrong. The backend includes dedicated health monitoring endpoints for administrators to check server status and database connections.",
    },
    {
        "id": "qa-22",
        "question": "Can I see my search history?",
        "answer": "The backend automatically tracks each search query with a unique identifier for performance monitoring. Your user dashboard may include a Search History section. Log in and look for a history log within your dashboard or profile area.",
    },
    {
        "id": "qa-23",
        "question": "How do I log out of my account?",
        "answer": "Find your username or avatar icon in the top-right corner of the navigation bar. Click on it to open a dropdown menu. Look for a Logout or Sign Out option and click it. This will log you out and redirect you to the homepage or login page.",
    },
    {
        "id": "qa-24",
        "question": "What browsers are supported by the platform?",
        "answer": "The platform fully supports the latest stable versions of all major web browsers including Google Chrome, Mozilla Firefox, Apple Safari, and Microsoft Edge. For the best experience, keep your browser updated to the most current version.",
    },
    {
        "id": "qa-25",
        "question": "Can I use the platform on mobile devices?",
        "answer": "Yes, the platform has a responsive layout that automatically adapts to fit different screen sizes including desktops, tablets, and smartphones. Buttons, menus, and forms are sized appropriately for touch interaction. All core features remain accessible on mobile browsers.",
    },
    {
        "id": "qa-26",
        "question": "How do I get help or support?",
        "answer": "Look for a Help, FAQ, or User Guide link in the website footer. If you cannot find an answer, there is a Contact Us page or support email address. For technical issues, account problems, or bugs, reach out to the system administrators via the provided contact information.",
    },
    {
        "id": "qa-27",
        "question": "What happens after I upload a document?",
        "answer": "The PDF is securely uploaded and temporarily stored. The system extracts plain text, analyzes it using NLP, creates a TF-IDF vector, compares it against all cases in the database using cosine similarity, compiles a ranked list of similar cases, and displays the results with titles, scores, and download links.",
    },
    {
        "id": "qa-28",
        "question": "How long does it take to process uploaded documents?",
        "answer": "For a standard legal document, the entire pipeline from upload to result display is usually completed within seconds. Larger documents take slightly longer. During high user activity, processing times may increase marginally. The total processing time is often displayed along with the results.",
    },
    {
        "id": "qa-29",
        "question": "Can I upload multiple documents at once?",
        "answer": "The current version processes one document per search. The similarity search is optimized to analyze a single case file against the database. If you need to analyze multiple documents, perform separate searches uploading one document at a time. Bulk upload is not currently supported.",
    },
    {
        "id": "qa-30",
        "question": "How do I access the API documentation?",
        "answer": "You can access the interactive API documentation by appending /docs to the base URL of the backend service (e.g., http://backend-server-address/docs). This documentation page is interactive, allowing developers to test API calls directly from their browser and see example requests and responses.",
    },
]


def main():
    print(f"Connecting to ChromaDB at: {PERSIST_DIR}")
    client = chromadb.PersistentClient(path=PERSIST_DIR)
    collection = client.get_or_create_collection("legal_cases")

    # Prepare documents for ingestion
    ids = []
    documents = []
    metadatas = []

    for item in KNOWLEDGE_BASE:
        doc_text = f"Q: {item['question']}\nA: {item['answer']}"
        ids.append(item["id"])
        documents.append(doc_text)
        metadatas.append({
            "case_id": item["id"],
            "title": item["question"],
            "source": "platform-qa-knowledge-base",
        })

    # Upsert (add or update) into the collection
    print(f"Upserting {len(documents)} Q&A entries into ChromaDB...")
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    # Verify
    count = collection.count()
    print(f"Done. Collection now has {count} total documents.")


if __name__ == "__main__":
    main()
