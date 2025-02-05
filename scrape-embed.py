import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import urllib3
import pdfplumber
import chromadb
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


EMBEDDING_MODEL = "text-embedding-3-large"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = "https://www.ammc.ma/fr/liste-etats-financiers-emetteurs?field_emetteur_target_id_verf=All&field_annee_value_1=All&page="
base_site = "https://www.ammc.ma"
data_dir = "pdf_documents"
os.makedirs(data_dir, exist_ok=True)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection(name="ammc_reports")

openai_embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, openai_api_key=OPENAI_API_KEY)

all_data = []

for page in range(18):
    url = f"{base_url}{page}"
    print(f"🔍 Scraping page {page + 1}...")

    response = requests.get(url, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')

    rows = soup.find_all('tr')

    for row in rows:
        emetteur_tag = row.find('td', class_='views-field-field-emetteur')
        emetteur = "N/A"
        if emetteur_tag:
            emetteur_links = emetteur_tag.find_all('a')
            if len(emetteur_links) > 1:
                emetteur = emetteur_links[1].get_text(strip=True)

        annee_tag = row.find('td', class_='views-field-field-annee')
        annee = annee_tag.find('time').get_text(strip=True) if annee_tag else "N/A"

        type_rapport_tag = row.find('td', class_='views-field-field-type-rapp-ef-em')
        if type_rapport_tag and type_rapport_tag.find('a'):
            type_rapport_link = base_site + type_rapport_tag.find('a')['href']
            type_rapport_text = type_rapport_tag.find('a').get_text(strip=True)
        else:
            type_rapport_link, type_rapport_text = "N/A", "N/A"

        if type_rapport_link == "N/A":
            print(f"⚠️ No valid report link found for {emetteur} ({annee}). Skipping.")
            continue  

        print(f" valid report link found fo {emetteur} ({annee}).")

        response_pdf = requests.get(type_rapport_link, verify=False)
        soup_pdf = BeautifulSoup(response_pdf.content, 'html.parser')
        document = soup_pdf.find('span', class_='file--mime-application-pdf')

        if document and document.find('a', href=True):
            pdf_link = document.find('a', href=True)['href']
            pdf_name = document.find('a', href=True).get_text(strip=True)

            pdf_url = base_site + pdf_link if not pdf_link.startswith("http") else pdf_link

            pdf_path = os.path.join(data_dir, pdf_name.replace("/", "_") + ".pdf")
            pdf_response = requests.get(pdf_url, verify=False)

            with open(pdf_path, 'wb') as f:
                f.write(pdf_response.content)

            print(f"📄 Downloaded: {pdf_name} ({pdf_url})")

            extracted_text = ""
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        text = page.extract_text()
                        if text:
                            extracted_text += text + "\n"

            except Exception as e:
                print(f"⚠️ Error extracting PDF {pdf_name}: {e}")

            if not extracted_text.strip():
                print(f"⚠️ Skipping embedding for {pdf_name} (Empty content).")
                continue

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            documents = text_splitter.split_text(extracted_text)

            langchain_docs = [
                Document(page_content=text, metadata={"source": pdf_name, "url": pdf_url, "emetteur": emetteur, "annee": annee})
                for text in documents
            ]

            try:
                vector_db = Chroma.from_documents(langchain_docs, openai_embeddings, persist_directory="./chroma_db")
            except ValueError as ve:
                print(f"⚠️ Skipping {pdf_name} due to empty embeddings: {ve}")
                continue

            all_data.append([emetteur, annee, type_rapport_text, pdf_url, pdf_name])

    time.sleep(2)  # Avoid getting blocked

df = pd.DataFrame(all_data, columns=["Émetteur", "Année", "Type Rapport", "PDF URL", "PDF Name"])
df.to_csv("financial_reports_metadata.csv", index=False, encoding='utf-8')

print("✅ Scraping completed, PDFs saved, and embeddings stored in ChromaDB.")

