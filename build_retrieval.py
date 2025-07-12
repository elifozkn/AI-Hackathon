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



API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

EMBED_MODEL = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")




def load_index():
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

