import ast
import re
import openai
import pandas as pd 
import os
import json
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle
from rank_bm25 import BM25Okapi
from openai import OpenAI
import asyncio



API_KEY = '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'
product_data = pd.read_csv(r'C:\Users\elif.yozkan\Desktop\AITS\evaluate_existing_rag\test_data\sampled_data.csv')
base_dir = r'C:\Users\elif.yozkan\Desktop\AITS\processing\parsed_manuals_new'
client = OpenAI(api_key=API_KEY)

EMBED_MODEL = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")


def get_products_with_manuals():
    # List to store product names that have non-empty manuals
    products_with_manuals = []

    # Walk through each product folder
    for product_folder in os.listdir(base_dir):
        product_path = os.path.join(base_dir, product_folder)
        
        if os.path.isdir(product_path):
            # Check all .md files in this product folder
            for file_name in os.listdir(product_path):
                if file_name.endswith('.md'):
                    file_path = os.path.join(product_path, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:  # Manual is not empty
                            products_with_manuals.append(product_folder)
                            break  # No need to check other files in the folder
    product_data = pd.read_csv(r'C:\Users\elif.yozkan\Desktop\AITS\evaluate_existing_rag\test_data\sampled_data.csv')
    product_data = product_data.loc[(product_data['PartName'].isin(products_with_manuals)) | (product_data['ModelName'].isin(products_with_manuals))]
    return product_data


def read_manual_text(product_id):
    manual_folder = os.path.join(base_dir, product_id)
    combined_text = []

    if os.path.exists(manual_folder):
        for file_name in os.listdir(manual_folder):
            if file_name.endswith('.md'):
                file_path = os.path.join(manual_folder, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    combined_text.append(f.read())
    
    return "\n".join(combined_text).strip()


def split_manual_sections(text):
    # Use regex to find section headers
    pattern = r'(?:^|\n)(\d*#.*?)\n'
    
    # Find all the section headers
    matches = list(re.finditer(pattern, text))
    
    sections = []
    
    for i in range(len(matches)):
        start = matches[i].end()
        if i+1 < len(matches):
            end = matches[i+1].start()
        else:
            end = len(text)
            
        header = matches[i].group(1).strip()
        content = text[start:end].strip()
        sections.append({'header': header, 'content': content})
    
    return sections
def prepare_data():
    ls = ['AIMB-217N-S6A1E',
 'AIMB-217N-S6A2E' ,'ARK-11-S1A2',
 'ADAM-3600-C2GL1A1E']
    product_data = get_products_with_manuals()
    product_data['manual_text'] = product_data['PartName'].apply(read_manual_text)
    product_data['manual_text'] = product_data['ModelName'].apply(read_manual_text)
    product_data = product_data.loc[product_data['manual_text'].str.strip() != '']
    product_data = product_data.loc[product_data['PartName'].str.match(r'^[A-Za-z]')]
    product_data = product_data.loc[product_data['PartName'].isin(ls)]
    
    product_data['manual_text'] = product_data['manual_text'].apply(split_manual_sections)
    product_data = product_data[['PartName','ModelName','NormalizedProductInformation','CorpSiteURL','Parent','Family','manual_text']]
    return product_data

def create_chunks(data): 
    
    df = data
    chunks = []

    for idx, row in df.iterrows():
        part_name = row["PartName"]
        model_name = row["ModelName"]
        family = row["Family"]
        parent = row['Parent']

        # Parse JSON columns safely
        try:
            manual_sections = row["manual_text"]
            if isinstance(manual_sections, str):
                manual_sections = ast.literal_eval(manual_sections)  # safely parse Python list as string
        except Exception as e:
            print(f"Parsing failed for row {row['PartName']}: {e}")
            manual_sections = []
            
            
          

        try:
            product_info = json.loads(row["NormalizedProductInformation"].replace("'", "\""))
        except:
            product_info = {}

        # 1. Manual chunks
        for section in manual_sections:
            header = section.get("header", "")
            content = section.get("content", "")
            if content.strip():
                chunks.append({
                    "text": f"[{model_name}] {header}\n{content}",
                    "meta": {"model": model_name, "part": part_name, "type": "manual", "family": family,"parent":parent}})

        # 2. Features
        for feat in product_info.get("Features", []):
            chunks.append({
                "text": f"[{model_name}] Feature: {feat}",
                "meta": {"model": model_name, "part": part_name, "type": "feature", "family": family,"parent":parent}
            })

        # 3. Specs
        for spec in product_info.get("Specs", []):
            cat = spec.get("SpecsCategoryName", "")
            name = spec.get("SpecsName", "")
            val = spec.get("SpecsValueName", "")
            chunks.append({
                "text": f"[{model_name}] {cat} - {name}: {val}",
                "meta": {"model": model_name, "part": part_name, "type": "spec", "family": family,"parent":parent}
            })

        # 4. Parent model description
        desc = product_info.get("ParentModelDesc", "")
        if desc:
            chunks.append({
                "text": f"[{model_name}] Description: {desc}",
                "meta": {"model": model_name, "part": part_name, "type": "desc", "family": family,"parent":parent}
            })
    print(len(chunks))
    return chunks 

def create_embeddings(chunks):
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True) 
    return embeddings,texts   
        
def build_faiss(embeddings,texts,chunks): 
# Build index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Save everything
    faiss.write_index(index, "vector_index.faiss")
    np.save("mpnet_embeddings.npy", embeddings)

    with open("texts.pkl", "wb") as f:
        pickle.dump(texts, f)

    with open("metadata.pkl", "wb") as f:
        pickle.dump([chunk["meta"] for chunk in chunks], f)



def build():
    data = prepare_data()
    print('prepared data')
    chunks = create_chunks(data)
    print('created chunks')
    print('creating embeddings')
    embeddings,texts = create_embeddings(chunks)
    print('embeddings are created')
    build_faiss(embeddings,texts,chunks)
    print('database')

    tokenized_corpus = [re.findall(r"\w+", text.lower()) for text in texts]
    bm25 = BM25Okapi(tokenized_corpus)

    return bm25


def build_if_missing():
    if not all(os.path.exists(p) for p in ["vector_index.faiss", "texts.pkl", "metadata.pkl", "bm25.pkl"]):
        print("Building vector and lexical index...")
        data = prepare_data()
        print('Prepared data')

        chunks = create_chunks(data)
        print('Created chunks')

        embeddings, texts = create_embeddings(chunks)
        print('Embeddings created')

        build_faiss(embeddings, texts, chunks)
        print('Vector DB created')

        # Build and save BM25
        tokenized_corpus = [re.findall(r"\w+", text.lower()) for text in texts]
        bm25 = BM25Okapi(tokenized_corpus)
        with open("bm25.pkl", "wb") as f:
            pickle.dump(bm25, f)

        print("BM25 index created and saved")
    else:
        print("Vector index and BM25 already exist. Skipping build.")


def load_index():
    build_if_missing()
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    faiss_path = os.path.join(BASE_DIR, "vector_index.faiss")
    index = faiss.read_index(faiss_path)
    texts_path = os.path.join(BASE_DIR, "texts.pkl")
    metadata_path = os.path.join(BASE_DIR, "metadata.pkl")
    bm25_path = os.path.join(BASE_DIR, "bm25.pkl")

    # Load the data
    with open(texts_path, "rb") as f:
        texts = pickle.load(f)

    with open(metadata_path, "rb") as f:
        metadata = pickle.load(f)

    with open(bm25_path, "rb") as f:
        bm25 = pickle.load(f)
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

    return index, texts, metadata, bm25, model


def rewrite_and_parse_query(query):
    prompt = f"""
You are a helpful assistant in a technical support system for industrial products.

Given the user query:
"{query}"

Please:
1. Rewrite the query only if there are multiple requests/intent otherwise keep the original.
2. Extract the **product model** mentioned (e.g., AFE-3600).
3. Classify the intent into one of the following categories, if there are multiple intents classify as other.:
   - spec_request : when the user asks for specifications of a product 
   - instruction : when the user asks for some instructions, how-to s regarding a product
   - troubleshooting : when the user asks for instructions to troubleshoot the issue they have
   - product information : when the user asks for detail about the attributes/features of a product
   - product discovery : when the user is trying to explore the available products, given a attribute/usecase of interest 
   - other

Respond in this JSON format:
{{
  "rewritten_query": "...",
  "product_of_interest": "...",
  "intent": "...",
}}
    """

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        result = json.loads(response.choices[0].message.content)
        print(result)
        return result
    except Exception as e:
        print(f"[ERROR parsing LLM output] {e}")
        return {
            "rewritten_query": query,
            "product_of_interest": extract_model_name(query),
            "intent": "other",
            "category": None,
            "family": None,
            "specs": []
        }



def extract_model_name(query): 
    match = re.search(r"\b(AFE-[\w\d]+|ARK-[\w\d]+|ADAM-[\w\d]+|UNO-[\w\d]+|ROM-[\w\d]+)\b", query.upper())
    return match.group(1) if match else None


def rewrite_and_parse_query_multi(query):
    prompt = f"""
You are a helpful assistant in a technical support system for industrial products.

Given the user query:
"{query}"

If the query contains multiple distinct tasks or intents (e.g., installation + specs), split it accordingly.

For each subquery:
1. Rewrite it for clarity.
2. Extract the **product model** mentioned (e.g., AFE-3600).
3. Classify the intent into one of:
   - spec_request
   - instruction
   - troubleshooting
   - product information
   - product discovery
   - other

Respond in this JSON list format:
[
  {{
    "rewritten_query": "...",
    "product_of_interest": "...",
    "intent": "..."
  }},
  ...
]
"""

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[ERROR parsing LLM output] {e}")
        return [{
            "rewritten_query": query,
            "product_of_interest": extract_model_name(query),
            "intent": "other"
        }]




def hybrid_search(query, faiss_index, bm25, texts, metadata, k=5, alpha=0.5, use_llm=True):
    parsed_list = rewrite_and_parse_query_multi(query) if use_llm else [{
        "rewritten_query": query,
        "product_of_interest": extract_model_name(query),
        "intent": "other"
    }]

    all_results = []

    for parsed in parsed_list:
        rewritten_query = parsed["rewritten_query"]
        model_name = parsed["product_of_interest"]
        intent = parsed["intent"]

        print(f"🧠 Query: {rewritten_query} | 🔍 Model: {model_name} | 🎯 Intent: {intent}")

        # Filtering rules
        def is_relevant(meta):
            doc_type = meta.get("type", "").lower()
            if intent in ["product discovery", "product information", "spec_request"]:
                return doc_type in ["spec", "feature", 'desc']
            elif intent in ["instruction", "troubleshooting"]:
                return doc_type in ["manual"]
            else:
                return True

        def is_model_match(meta):
            if not model_name:
                return True
            model_name_upper = model_name.upper()
            return (
                meta.get("model", "").upper() == model_name_upper or
                meta.get("family", "").upper() == model_name_upper or
                meta.get("part", "").upper() == model_name_upper
            )

        valid_indices = [
            i for i, meta in enumerate(metadata)
            if is_relevant(meta) and is_model_match(meta)
        ]

        if not valid_indices:
            print(f"No relevant chunks found for model: {model_name} with intent: {intent}")
            continue

        query_emb = EMBED_MODEL.encode([rewritten_query], convert_to_numpy=True)
        _, faiss_indices = faiss_index.search(query_emb, k * 10)
        faiss_scores = {i: 1 / (1 + idx) for idx, i in enumerate(faiss_indices[0]) if i in valid_indices}

        tokenized_query = re.findall(r"\w+", rewritten_query.lower())
        bm25_scores = bm25.get_scores(tokenized_query)
        bm25_top = sorted([(i, score) for i, score in enumerate(bm25_scores) if i in valid_indices], key=lambda x: x[1], reverse=True)[:k * 10]
        bm25_scores_dict = {i: s for i, s in bm25_top}

        all_indices = set(faiss_scores) | set(bm25_scores_dict)
        hybrid_rank = [
            (i, alpha * faiss_scores.get(i, 0) + (1 - alpha) * bm25_scores_dict.get(i, 0))
            for i in all_indices
        ]

        top_hits = sorted(hybrid_rank, key=lambda x: x[1], reverse=True)[:k]
        results = [{"text": texts[i], "meta": metadata[i], "intent": intent} for i,score in top_hits]
        all_results.extend(results)

    return all_results


build_if_missing()