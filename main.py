import arxiv
import requests
import streamlit as st
import fitz  # PyMuPDF for PDF text extraction
from transformers import pipeline
import os

# 1. Define the directories for storing PDFs and text files
PDF_DIR = "arxiv_pdfs"
TEXT_DIR = "extracted_texts"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)

# 2. Cache the summarizer to avoid reloading the model each time
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="t5-small")

summarizer = load_summarizer()

# 3. Fetch recent papers from arXiv in the Robotics category
def fetch_arxiv_papers(query="cs.RO", max_results=1):
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    return search.results()

# 4. Download and extract text from PDFs
def download_and_extract_text(paper):
    try:
        pdf_url = paper.pdf_url
        title_safe = paper.title.replace(':', '_').replace('/', '_')  # Handle unsafe characters
        pdf_file_name = os.path.join(PDF_DIR, f"{title_safe}.pdf")

        # Download PDF if not already downloaded
        if not os.path.exists(pdf_file_name):
            response = requests.get(pdf_url, allow_redirects=True)
            if response.status_code == 200:
                with open(pdf_file_name, 'wb') as f:
                    f.write(response.content)
            else:
                return None, f"Failed to download {pdf_file_name}. Status code: {response.status_code}"

        # Extract text from the downloaded PDF
        doc = fitz.open(pdf_file_name)
        text = "".join([doc.load_page(page_num).get_text() for page_num in range(doc.page_count)])
        if not text:
            return None, "No text extracted from the PDF."

        return text, None

    except Exception as e:
        return None, f"Error downloading or extracting text: {e}"

# 5. Summarize text
def summarize_text(text):
    return summarizer(text, max_length=8000, min_length=100, do_sample=False)[0]['summary_text']

# 6. Categorize papers based on predefined subdomains
def categorize_paper(text):
    categories = {
        "Control Systems": ["control", "feedback", "dynamics"],
        "Robot Vision": ["vision", "image", "camera"],
        "Robot Learning": ["learning", "reinforcement", "training"]
    }
    for category, keywords in categories.items():
        if any(keyword in text.lower() for keyword in keywords):
            return category
    return "Uncategorized"

# 7. Process arXiv papers
def process_arxiv_papers(max_results):
    papers = fetch_arxiv_papers(max_results=max_results)
    results = []

    for paper in papers:
        title = paper.title
        extracted_text, error = download_and_extract_text(paper)
        
        if error:
            print(error)
            continue
        
        if extracted_text:
            summary = summarize_text(extracted_text[:5000])
            category = categorize_paper(extracted_text)
            results.append({
                "title": title,
                "summary": summary,
                "category": category
            })

    return results

# 8. Display the results in Streamlit
def display_summary_dashboard(results):
    st.title("Arxiv Paper Summaries")

    for result in results:
        st.header(result['title'])
        st.subheader(f"Category: {result['category']}")
        st.write(result['summary'])
        st.write("---")

# Main function to execute the pipeline
if __name__ == "__main__":
    # Add a number input for the max_results value
    max_results = st.number_input("Enter the number of papers to fetch:", min_value=1, max_value=100, value=5)
    
    if st.button("Fetch and Process Papers"):
        # Fetch and process papers based on user input for max_results
        results = process_arxiv_papers(max_results=max_results)
        
        if results:
            display_summary_dashboard(results)
        else:
            st.write("No papers were processed or an error occurred.")
