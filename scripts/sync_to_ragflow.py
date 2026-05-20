"""
sync_to_ragflow.py
Pulls all approved/*.md files from GitHub and upserts them into a RAGFlow dataset.
"""
import os
import time
from github import Github
from ragflow_sdk import RAGFlow

# ── Config ──────────────────────────────────────────────────────────
GITHUB_TOKEN    = os.environ["GITHUB_TOKEN"]       # GitHub PAT
RAGFLOW_API_KEY = os.environ.get("RAGFLOW_API_KEY","ragflow-YVYdLdNalUCxSOxKaaf-2HLPW6R2nRofyPuQxljKIWo")    # RAGFlow API key
RAGFLOW_BASE_URL = os.environ.get("RAGFLOW_BASE_URL", "https://singh-acrobat-bundle-steel.trycloudflare.com")
REPO_NAME       = "Amos-lin/squirrelai-skills"
APPROVED_PATH   = "approved"
DATASET_NAME    = "销冠 Skill 库"
# ────────────────────────────────────────────────────────────────────

def get_approved_files(repo):
    """Recursively fetch all .md files under approved/"""
    results = []
    contents = repo.get_contents(APPROVED_PATH)
    while contents:
        item = contents.pop(0)
        if item.type == "dir":
            contents.extend(repo.get_contents(item.path))
        elif item.name.endswith(".md"):
            results.append(item)
    return results

def get_or_create_dataset(rag: RAGFlow) -> object:
    datasets = rag.list_datasets(name=DATASET_NAME)
    if datasets:
        print(f"Using existing dataset: {DATASET_NAME}")
        return datasets[0]
    print(f"Creating new dataset: {DATASET_NAME}")
    return rag.create_dataset(
        name=DATASET_NAME,
        chunk_method="naive",        # best for Markdown text
        language="Chinese",          # your skills are in Chinese
        embedding_model="BAAI/bge-m3@BAAI"
    )

def sync():
    # 1. Connect to GitHub
    gh   = Github(GITHUB_TOKEN)
    repo = gh.get_repo(REPO_NAME)
    md_files = get_approved_files(repo)
    print(f"Found {len(md_files)} approved .md files in GitHub")

    # 2. Connect to RAGFlow
    rag     = RAGFlow(api_key=RAGFLOW_API_KEY, base_url=RAGFLOW_BASE_URL)
    dataset = get_or_create_dataset(rag)

    # 3. Get existing doc names to avoid duplicates
    existing = {doc.name for doc in dataset.list_documents()}

    # 4. Upload new/changed files
    to_upload = []
    for f in md_files:
        doc_name = f.path.replace("/", "__") + ".md"  # flatten path as doc name
        content  = f.decoded_content                  # raw bytes
        to_upload.append({"name": doc_name, "blob": content})

    if not to_upload:
        print("Nothing to upload.")
        return

    print(f"Uploading {len(to_upload)} documents...")
    dataset.upload_documents(to_upload)

    # 5. Parse / chunk uploaded documents
    time.sleep(2)  # brief wait for upload to register
    docs = dataset.list_documents()
    ids  = [doc.id for doc in docs]
    dataset.async_parse_documents(ids)
    print(f"Parsing triggered for {len(ids)} documents. Done.")

if __name__ == "__main__":
    sync()