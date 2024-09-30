import arxiv
import requests
import fitz  # PyMuPDF for PDF text extraction
from transformers import pipeline
import os

# 1. Define the directories for storing PDFs and text files
PDF_DIR = "arxiv_pdfs"
TEXT_DIR = "extracted_texts"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(TEXT_DIR, exist_ok=True)

# 2. Fetch recent papers from arXiv in the Robotics category
def fetch_arxiv_papers(query="cs.RO", max_results=5):
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    return search.results()

# 3. Download the PDFs of the papers
def download_pdf(url, file_name):
    try:
        # Follow redirects to ensure we reach the correct URL
        response = requests.get(url, allow_redirects=True)
        
        # Check if the response is OK (200 status code)
        if response.status_code == 200:
            # Make sure file has .pdf extension
            if not file_name.endswith(".pdf"):
                file_name += ".pdf"
            print("file_name::::",file_name)
            with open(file_name, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {file_name}")
        else:
            print(f"Failed to download {file_name}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading {file_name}: {e}")

# 4. Extract text from PDFs
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text += page.get_text()
    return text

# 5. Summarize text using an LLM (Hugging Face T5 model)
def summarize_text(text):
    summarizer = pipeline("summarization", model="t5-small")  # You can use t5-base for larger summaries
    summary = summarizer(text, max_length=8000, min_length=100, do_sample=False)
    return summary[0]['summary_text']

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

# 7. Process pipeline
def process_arxiv_papers():
    # Fetch arXiv papers
    papers = fetch_arxiv_papers()
    
    results = []
    
    for paper in papers:
        title = paper.title
        pdf_url = paper.pdf_url
        pdf_file_name = f"{PDF_DIR}\\{title.replace(':', '_')}.pdf"
        # Download PDF
        download_pdf(pdf_url, pdf_file_name)
        
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(pdf_file_name)
        if not extracted_text:
            continue  # Skip to the next paper if extraction fails
        
        text_file_name = f"{TEXT_DIR}/{title.replace(':', '_')}.txt"
        try:
            with open(text_file_name, 'w', encoding='utf-8') as text_file:
                text_file.write(extracted_text)
        except Exception as e:
            print(f"Error writing to file {text_file_name}: {e}")
            continue
        
        # Summarize the text (limit to 2000 characters to avoid performance issues)
        summary = summarize_text(extracted_text[:5000])
        
        # Categorize the paper
        category = categorize_paper(extracted_text)
        
        # Save results
        results.append({
            "title": title,
            "summary": summary,
            "category": category
        })
    
    return results

# 8. Output the results
def save_results(results, output_file="arxiv_summary.txt"):
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(f"Title: {result['title']}\n")
            f.write(f"Category: {result['category']}\n")
            f.write(f"Summary: {result['summary']}\n")
            f.write("="*50 + "\n\n")
    print(f"Results saved to {output_file}")

# Main function to execute the pipeline
if __name__ == "__main__":
    results = process_arxiv_papers()
    save_results(results)
