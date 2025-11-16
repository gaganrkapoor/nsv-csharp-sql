#!/usr/bin/env python3
"""
LangChain Pipeline for Invoice Product Matching
Implements the complete workflow: Clean → Embed → Search → Match → Learn
"""

import re
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

# Database and vector imports
import pyodbc
import chromadb
from chromadb.config import Settings


@dataclass
class InvoiceLineItem:
    """Represents a line item from an invoice"""
    description: str
    quantity: float
    unit_price: float
    total_price: float
    line_number: int
    raw_description: str


@dataclass
class ProductMatch:
    """Represents a matched product with confidence"""
    product_id: int
    product_code: str
    product_name: str
    standardized_description: str
    confidence_score: float
    match_type: str  # 'exact', 'semantic', 'ai_resolved'
    alternative_descriptions: List[str] = None


class ProductMatchingPipeline:
    """
    LangChain pipeline for matching invoice descriptions to products
    """
    
    def __init__(self, 
                 sql_connection_string: str,
                 chromadb_host: str = "localhost",
                 chromadb_port: int = 8000,
                 openai_api_key: str = None,
                 embedding_model: str = "text-embedding-ada-002"):
        """
        Initialize the product matching pipeline
        
        Args:
            sql_connection_string: SQL Server connection string
            chromadb_host: ChromaDB host
            chromadb_port: ChromaDB port  
            openai_api_key: OpenAI API key
            embedding_model: Embedding model to use
        """
        self.sql_connection_string = sql_connection_string
        self.chromadb_host = chromadb_host
        self.chromadb_port = chromadb_port
        
        # Initialize LangChain components
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            model=embedding_model
        ) if openai_api_key else None
        
        self.llm = ChatOpenAI(
            openai_api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.1
        ) if openai_api_key else None
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.HttpClient(
            host=chromadb_host,
            port=chromadb_port
        )
        
        # Collection for product embeddings
        self.collection_name = "product_descriptions"
        
        # Text processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=200,
            chunk_overlap=20,
            separators=[",", ";", " and ", " & "]
        )
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def clean_and_normalize_description(self, description: str) -> str:
        """
        Clean and normalize product description for better matching
        
        Args:
            description: Raw product description from invoice
            
        Returns:
            Cleaned and normalized description
        """
        if not description:
            return ""
        
        # Convert to lowercase
        clean_desc = description.lower().strip()
        
        # Remove common invoice artifacts
        clean_desc = re.sub(r'\b(qty|quantity|ea|each|unit|units|item|items)\b', '', clean_desc)
        clean_desc = re.sub(r'\b\d+\s*(x|×|by)\s*\d+\b', lambda m: m.group(0).replace(' ', ''), clean_desc)
        
        # Standardize measurements
        clean_desc = re.sub(r'\b(\d+)\s*mm\b', r'\1mm', clean_desc)
        clean_desc = re.sub(r'\b(\d+)\s*m\b', r'\1m', clean_desc)
        clean_desc = re.sub(r'\b(\d+)\s*cm\b', r'\1cm', clean_desc)
        
        # Standardize common abbreviations
        replacements = {
            'galvanised': 'galvanized',
            'galv': 'galvanized', 
            'ss': 'stainless steel',
            'st steel': 'stainless steel',
            'hw': 'hardwood',
            'sw': 'softwood',
            'dar': 'dressed all round',
            'ddr': 'dressed dual radius',
            'h4': 'treated h4',
            'treated': 'treated h3'
        }
        
        for old, new in replacements.items():
            clean_desc = re.sub(r'\b' + re.escape(old) + r'\b', new, clean_desc)
        
        # Remove extra whitespace
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
        
        return clean_desc
    
    def extract_line_items(self, invoice_json: Dict) -> List[InvoiceLineItem]:
        """
        Extract line items from Document Intelligence JSON
        
        Args:
            invoice_json: JSON output from Azure Document Intelligence
            
        Returns:
            List of InvoiceLineItem objects
        """
        line_items = []
        
        # Handle different Document Intelligence response formats
        if 'Items' in invoice_json:
            items = invoice_json['Items']
        elif 'analyzeResult' in invoice_json:
            # Handle full Document Intelligence response
            documents = invoice_json['analyzeResult'].get('documents', [])
            if documents and 'fields' in documents[0]:
                fields = documents[0]['fields']
                items = fields.get('Items', {}).get('valueArray', [])
            else:
                items = []
        else:
            items = []
        
        for i, item in enumerate(items):
            try:
                # Extract item fields based on Document Intelligence format
                if isinstance(item, dict):
                    description = item.get('Description', {}).get('valueString', '') or \
                                item.get('description', '') or \
                                item.get('ProductCode', {}).get('valueString', '')
                    
                    quantity = float(item.get('Quantity', {}).get('valueNumber', 0) or \
                                   item.get('quantity', 0) or 1.0)
                    
                    unit_price = float(item.get('UnitPrice', {}).get('valueNumber', 0) or \
                                     item.get('unit_price', 0) or 0.0)
                    
                    total_price = float(item.get('Amount', {}).get('valueNumber', 0) or \
                                      item.get('total', 0) or \
                                      quantity * unit_price)
                
                if description:
                    line_item = InvoiceLineItem(
                        description=self.clean_and_normalize_description(description),
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price,
                        line_number=i + 1,
                        raw_description=description
                    )
                    line_items.append(line_item)
                    
            except (ValueError, TypeError, KeyError) as e:
                self.logger.warning(f"Error processing line item {i}: {e}")
                continue
        
        return line_items
    
    def get_product_embeddings_from_db(self) -> List[Dict]:
        """
        Load product data and embeddings from SQL database
        
        Returns:
            List of product dictionaries with embeddings
        """
        products = []
        
        try:
            conn = pyodbc.connect(self.sql_connection_string)
            cursor = conn.cursor()
            
            # Get products with their descriptions
            query = """
            SELECT DISTINCT
                p.ProductId, p.ProductCode, p.ProductName, 
                p.StandardizedDescription, p.Brand, c.CategoryName,
                pd.AlternativeDescription, pd.DescriptionType, pd.Supplier
            FROM Products p
            LEFT JOIN Categories c ON p.CategoryId = c.CategoryId
            LEFT JOIN ProductDescriptions pd ON p.ProductId = pd.ProductId
            WHERE p.IsActive = 1
            ORDER BY p.ProductId
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            current_product = None
            
            for row in rows:
                if current_product is None or current_product['product_id'] != row[0]:
                    # New product
                    current_product = {
                        'product_id': row[0],
                        'product_code': row[1],
                        'product_name': row[2],
                        'standardized_description': row[3],
                        'brand': row[4],
                        'category': row[5],
                        'alternative_descriptions': []
                    }
                    products.append(current_product)
                
                # Add alternative description if exists
                if row[6]:  # AlternativeDescription
                    current_product['alternative_descriptions'].append({
                        'description': row[6],
                        'type': row[7],
                        'supplier': row[8]
                    })
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error loading products from database: {e}")
        
        return products
    
    def build_vector_index(self, rebuild: bool = False):
        """
        Build or rebuild the ChromaDB vector index for products
        
        Args:
            rebuild: Whether to rebuild the entire index
        """
        try:
            # Get or create collection
            if rebuild:
                try:
                    self.chroma_client.delete_collection(name=self.collection_name)
                except:
                    pass
            
            collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Product descriptions for invoice matching"}
            )
            
            # Load products from database
            products = self.get_product_embeddings_from_db()
            
            if not products:
                self.logger.warning("No products found in database")
                return
            
            # Prepare documents for embedding
            documents = []
            metadatas = []
            ids = []
            
            for product in products:
                # Add main product description
                documents.append(product['standardized_description'])
                metadatas.append({
                    'product_id': product['product_id'],
                    'product_code': product['product_code'],
                    'product_name': product['product_name'],
                    'description_type': 'standardized',
                    'category': product['category'] or '',
                    'brand': product['brand'] or ''
                })
                ids.append(f"product_{product['product_id']}_std")
                
                # Add alternative descriptions
                for alt_desc in product['alternative_descriptions']:
                    documents.append(alt_desc['description'])
                    metadatas.append({
                        'product_id': product['product_id'],
                        'product_code': product['product_code'],
                        'product_name': product['product_name'],
                        'description_type': alt_desc['type'],
                        'supplier': alt_desc['supplier'] or '',
                        'category': product['category'] or '',
                        'brand': product['brand'] or ''
                    })
                    ids.append(f"product_{product['product_id']}_{alt_desc['type']}_{len(ids)}")
            
            # Add documents to collection (ChromaDB will handle embeddings)
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Built vector index with {len(documents)} product descriptions")
            
        except Exception as e:
            self.logger.error(f"Error building vector index: {e}")
    
    def search_similar_products(self, query_description: str, top_k: int = 5) -> List[Dict]:
        """
        Search for similar products using vector similarity
        
        Args:
            query_description: Cleaned product description to search for
            top_k: Number of top results to return
            
        Returns:
            List of similar products with similarity scores
        """
        try:
            collection = self.chroma_client.get_collection(name=self.collection_name)
            
            # Perform similarity search
            results = collection.query(
                query_texts=[query_description],
                n_results=top_k
            )
            
            similar_products = []
            
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if 'distances' in results else 0.0
                    
                    similar_products.append({
                        'product_id': metadata['product_id'],
                        'product_code': metadata['product_code'],
                        'product_name': metadata['product_name'],
                        'matched_description': doc,
                        'description_type': metadata['description_type'],
                        'similarity_score': 1.0 - distance,  # Convert distance to similarity
                        'metadata': metadata
                    })
            
            return similar_products
            
        except Exception as e:
            self.logger.error(f"Error searching similar products: {e}")
            return []
    
    def ai_resolve_best_match(self, invoice_description: str, candidates: List[Dict]) -> Optional[ProductMatch]:
        """
        Use AI to determine the best product match from candidates
        
        Args:
            invoice_description: Original invoice description
            candidates: List of candidate products from vector search
            
        Returns:
            Best product match with confidence score
        """
        if not self.llm or not candidates:
            return None
        
        # Create prompt for AI reasoning
        prompt_template = ChatPromptTemplate.from_template("""
        You are an expert in building materials and construction products. 
        
        Given an invoice line item description and candidate product matches, 
        determine which product is the best match and provide a confidence score.
        
        Invoice Description: "{invoice_description}"
        
        Candidate Products:
        {candidates_text}
        
        Please analyze each candidate and return:
        1. The best matching product ID
        2. Confidence score (0.0 to 1.0)
        3. Brief reasoning
        
        Return your answer in JSON format:
        {{
            "best_match_product_id": <product_id>,
            "confidence_score": <float>,
            "reasoning": "<brief explanation>"
        }}
        """)
        
        # Format candidates for AI
        candidates_text = ""
        for i, candidate in enumerate(candidates[:5], 1):
            candidates_text += f"""
        {i}. Product ID: {candidate['product_id']}
           Code: {candidate['product_code']}
           Name: {candidate['product_name']}
           Description: {candidate['matched_description']}
           Similarity: {candidate['similarity_score']:.3f}
        """
        
        try:
            # Create chain
            chain = prompt_template | self.llm | StrOutputParser()
            
            # Get AI response
            response = chain.invoke({
                "invoice_description": invoice_description,
                "candidates_text": candidates_text
            })
            
            # Parse JSON response
            ai_result = json.loads(response.strip())
            
            # Find the selected product
            selected_product = next(
                (c for c in candidates if c['product_id'] == ai_result['best_match_product_id']), 
                None
            )
            
            if selected_product:
                return ProductMatch(
                    product_id=selected_product['product_id'],
                    product_code=selected_product['product_code'], 
                    product_name=selected_product['product_name'],
                    standardized_description=selected_product['matched_description'],
                    confidence_score=ai_result['confidence_score'],
                    match_type='ai_resolved',
                    alternative_descriptions=[c['matched_description'] for c in candidates]
                )
            
        except Exception as e:
            self.logger.error(f"Error in AI resolution: {e}")
        
        return None
    
    def match_invoice_line_items(self, invoice_json: Dict, supplier: str = None) -> List[Dict]:
        """
        Complete pipeline: extract line items and match to products
        
        Args:
            invoice_json: JSON output from Document Intelligence
            supplier: Supplier name for context
            
        Returns:
            List of matched line items with product information
        """
        # Extract line items
        line_items = self.extract_line_items(invoice_json)
        
        matched_items = []
        
        for line_item in line_items:
            self.logger.info(f"Processing line item: {line_item.description}")
            
            # Search for similar products
            candidates = self.search_similar_products(line_item.description, top_k=5)
            
            best_match = None
            
            if candidates:
                # If we have a clear winner (high similarity), use it
                if candidates[0]['similarity_score'] > 0.9:
                    best_candidate = candidates[0]
                    best_match = ProductMatch(
                        product_id=best_candidate['product_id'],
                        product_code=best_candidate['product_code'],
                        product_name=best_candidate['product_name'],
                        standardized_description=best_candidate['matched_description'],
                        confidence_score=best_candidate['similarity_score'],
                        match_type='semantic',
                        alternative_descriptions=[c['matched_description'] for c in candidates]
                    )
                else:
                    # Use AI to resolve ambiguous matches
                    best_match = self.ai_resolve_best_match(line_item.raw_description, candidates)
            
            # Prepare result
            match_result = {
                'line_item': {
                    'description': line_item.description,
                    'raw_description': line_item.raw_description,
                    'quantity': line_item.quantity,
                    'unit_price': line_item.unit_price,
                    'total_price': line_item.total_price,
                    'line_number': line_item.line_number
                },
                'matched_product': best_match.__dict__ if best_match else None,
                'candidates': candidates[:3],  # Top 3 alternatives
                'needs_review': best_match is None or best_match.confidence_score < 0.7
            }
            
            matched_items.append(match_result)
        
        return matched_items
    
    def update_from_user_feedback(self, invoice_description: str, correct_product_id: int, supplier: str = None):
        """
        Update the vector database with user corrections
        
        Args:
            invoice_description: Original invoice description
            correct_product_id: Correct product ID selected by user
            supplier: Supplier for context
        """
        try:
            # Save training data to SQL
            conn = pyodbc.connect(self.sql_connection_string)
            cursor = conn.cursor()
            
            insert_query = """
            INSERT INTO ProductMatchingTraining 
            (InvoiceDescription, CorrectProductId, IsUserCorrected, InvoiceSupplier, CreatedBy)
            VALUES (?, ?, 1, ?, 'system')
            """
            
            cursor.execute(insert_query, 
                         (invoice_description, correct_product_id, supplier, ))
            conn.commit()
            conn.close()
            
            # Add new alternative description to product
            self._add_alternative_description(correct_product_id, invoice_description, 'user_feedback', supplier)
            
            # Rebuild vector index to include new training data
            self.build_vector_index(rebuild=True)
            
            self.logger.info(f"Updated training data: '{invoice_description}' -> Product {correct_product_id}")
            
        except Exception as e:
            self.logger.error(f"Error updating user feedback: {e}")
    
    def _add_alternative_description(self, product_id: int, description: str, desc_type: str, supplier: str = None):
        """Add alternative description to product"""
        try:
            conn = pyodbc.connect(self.sql_connection_string)
            cursor = conn.cursor()
            
            # Check if description already exists
            check_query = """
            SELECT COUNT(*) FROM ProductDescriptions 
            WHERE ProductId = ? AND AlternativeDescription = ?
            """
            cursor.execute(check_query, (product_id, description))
            
            if cursor.fetchone()[0] == 0:
                insert_query = """
                INSERT INTO ProductDescriptions (ProductId, AlternativeDescription, DescriptionType, Supplier)
                VALUES (?, ?, ?, ?)
                """
                cursor.execute(insert_query, (product_id, description, desc_type, supplier))
                conn.commit()
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error adding alternative description: {e}")