import logging
import os
from dotenv import load_dotenv
from langchain.indexes import SQLRecordManager, index
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
import weaviate
from weaviate.auth import AuthApiKey
from langchain_community.vectorstores import Weaviate
from langchain_weaviate.vectorstores import WeaviateVectorStore
from weaviate.classes.init import Auth
# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
WEAVIATE_DOCS_INDEX_NAME = "LangChain_Combined_Docs_OpenAI_text_embedding_3_small"


def get_embeddings_model():
    return OpenAIEmbeddings(model="text-embedding-3-small", chunk_size=200)


def load_txt_docs(folder_path: str):
    """
    Load text documents from a specified folder and return a list of document data.
    Each document contains the content and metadata with source as filename.
    """
    docs = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                docs.append({"content": content, "metadata": {"source": filename}})
                logger.info(f"Loaded content from {filename}.")
    return docs


def ingest_docs():
    # Load environment variables
    weaviate_url = os.environ["WEAVIATE_URL"]
    weaviate_api_key = os.environ["WEAVIATE_API_KEY"]
    record_manager_db_url = os.environ["RECORD_MANAGER_DB_URL"]
    txt_folder_path = os.environ.get("TXT_FOLDER_PATH")




    if not txt_folder_path or not os.path.isdir(txt_folder_path):
        raise ValueError("Please provide a valid path to the folder containing text files.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    embedding_model = get_embeddings_model()

    # Load documents from text files
    docs_from_txt_files = load_txt_docs(txt_folder_path)
    if not docs_from_txt_files:
        logger.error("No documents loaded from text files.")
        return

    # Split documents into chunks
    docs_transformed = []
    for doc in docs_from_txt_files:
        text_chunks = text_splitter.split_text(doc["content"])
        for chunk in text_chunks:
            if len(chunk) > 10:  # Filter out very small chunks
                docs_transformed.append(
                    Document(page_content=chunk, metadata=doc["metadata"])
                )

    # Ensure 'source' and 'title' metadata are present
    for doc in docs_transformed:
        if "source" not in doc.metadata:
            doc.metadata["source"] = ""
        if "title" not in doc.metadata:
            doc.metadata["title"] = ""
        # Connect to Weaviate Cloud
    with weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
    ) as client:
        try:
            vectorstore = WeaviateVectorStore(
                client=client,
                index_name=WEAVIATE_DOCS_INDEX_NAME,
                text_key="text",
                embedding=embedding_model,
                attributes=["source", "title"]
            )

            # Initialize record manager
            record_manager = SQLRecordManager(
                f"weaviate/{WEAVIATE_DOCS_INDEX_NAME}", db_url=record_manager_db_url
            )
            record_manager.create_schema()

            # Index documents in Weaviate
            indexing_stats = index(
                docs_transformed,
                record_manager,
                vectorstore,
                cleanup="full",
                source_id_key="source",
                force_update=True  # Force updates for all documents
            )
            logger.info(f"Indexing stats for text files: {indexing_stats}")

        except Exception as e:
            logger.error(f"An error occurred during indexing: {e}")

'''
if __name__ == "__main__":
    ingest_docs()
'''