"""
AI Utility Functions for Blog Platform
Uses OpenAI API for:
- Embeddings (semantic search)
- Text generation (summaries, tags, SEO)
"""
import os
import json
import numpy as np
from django.conf import settings
from openai import OpenAI

# Initialize OpenAI client
try:
    client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
except Exception:
    client = None


def generate_embedding(text: str) -> list:
    """
    Generate embedding vector for semantic search using OpenAI text-embedding-3-small
    
    Args:
        text: Input text to embed
        
    Returns:
        List of floats representing the embedding vector
    """
    if not client:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in environment.")
    
    try:
        # Clean and prepare text
        text = text.strip()
        if len(text) > 8000:  # Truncate if too long
            text = text[:8000]
        
        # Generate embedding
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []


def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Args:
        vec1: First vector
        vec2: Second vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    try:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    except Exception as e:
        print(f"Error calculating cosine similarity: {e}")
        return 0.0


def generate_summary(content: str, max_length: int = 200) -> str:
    """
    Generate AI summary for blog post using GPT-4.1-mini
    
    Args:
        content: Post content
        max_length: Maximum length of summary
        
    Returns:
        Generated summary text
    """
    if not client:
        return ""
    
    try:
        # Truncate content if too long
        if len(content) > 3000:
            content = content[:3000]
        
        prompt = f"""Generate a concise, engaging summary of the following blog post content. 
The summary should be no more than {max_length} characters and capture the main points and key takeaways.

Content:
{content}

Summary:"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise blog post summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Ensure summary doesn't exceed max_length
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(' ', 1)[0] + "..."
        
        return summary
    except Exception as e:
        print(f"Error generating summary: {e}")
        return ""


def generate_tags_and_category(content: str) -> dict:
    """
    Generate tags and category for blog post using GPT-4.1-mini
    
    Args:
        content: Post content
        
    Returns:
        Dictionary with 'category' (str) and 'tags' (list of 5 strings)
    """
    if not client:
        return {"category": "", "tags": []}
    
    try:
        # Truncate content if too long
        if len(content) > 3000:
            content = content[:3000]
        
        # Ensure content is substantial
        if len(content) < 50:
            print("WARNING: Content too short for analysis")
            return {"category": "General", "tags": ["blog", "article", "post", "content", "writing"]}
        
        prompt = f"""Analyze this blog post content and return a JSON object with exactly this structure:

{{
    "category": "exact category name here",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

REQUIREMENTS:
- category: Provide ONE specific category (examples: "Technology", "Health & Wellness", "Business", "Lifestyle", "Education", "Personal Development")
- tags: Provide EXACTLY 5 tags as an array of strings (each tag 1-2 words max)

BLOG POST CONTENT:
{content[:2500]}

You MUST provide actual values, not empty strings or empty arrays. Return only the JSON object."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a content classification expert. Always return valid JSON only. Never return empty arrays or empty strings."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7,
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        result_text = response.choices[0].message.content.strip()
        print(f"DEBUG: Raw AI response for tags: {result_text[:200]}...")
        
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        print(f"DEBUG: Extracted JSON: {result_text}")
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as je:
            print(f"DEBUG: JSON decode error: {je}")
            print(f"DEBUG: Attempting to fix JSON...")
            # Try to find JSON-like structure
            import re
            json_match = re.search(r'\{[^}]*"category"[^}]*\}', result_text)
            if json_match:
                result_text = json_match.group(0)
                result = json.loads(result_text)
            else:
                raise je
        
        category = result.get("category", "").strip()
        tags = result.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        
        print(f"DEBUG: Parsed category: {category}, tags: {tags}")
        
        return {
            "category": category,
            "tags": tags[:5] if tags else []  # Ensure max 5 tags
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating tags and category: {e}")
        
        # Check for quota/billing errors
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg.lower():
            print("ERROR: OpenAI API quota exceeded. Please add credits to your OpenAI account.")
        
        import traceback
        traceback.print_exc()
        return {"category": "", "tags": [], "error": "OpenAI API quota exceeded. Please check your billing."}


def generate_seo_metadata(title: str, content: str) -> dict:
    """
    Generate SEO metadata using GPT-4.1-mini
    
    Args:
        title: Post title
        content: Post content
        
    Returns:
        Dictionary with seo_title, meta_description, seo_keywords, slug_suggestion
    """
    if not client:
        return {
            "seo_title": title,
            "meta_description": "",
            "seo_keywords": [],
            "slug_suggestion": ""
        }
    
    try:
        # Truncate content if too long
        if len(content) > 2000:
            content = content[:2000]
        
        # Ensure content is substantial
        if len(content) < 50:
            print("WARNING: Content too short for SEO analysis")
            slug_base = title.lower().replace(' ', '-')[:50]
            return {
                "seo_title": title[:60],
                "meta_description": content[:147] if len(content) > 20 else title[:147],
                "seo_keywords": ["blog", "article", "post", "content", "writing", "read"],
                "slug_suggestion": slug_base
            }
        
        prompt = f"""Analyze this blog post and return a JSON object with exactly this structure:

{{
    "seo_title": "seo optimized title here",
    "meta_description": "compelling meta description here",
    "seo_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5", "keyword6"],
    "slug_suggestion": "url-slug-suggestion"
}}

REQUIREMENTS:
- seo_title: SEO-optimized title (max 60 chars, include main keyword, make it compelling)
- meta_description: Compelling meta description (max 150 chars, keyword-rich, engaging)
- seo_keywords: Provide EXACTLY 6 relevant SEO keywords as array
- slug_suggestion: URL-friendly slug (lowercase, use hyphens, max 50 chars, SEO-friendly)

BLOG POST:
Title: {title}
Content: {content[:2500]}

You MUST provide actual values for all fields. No empty strings or empty arrays. Return only the JSON object."""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an SEO expert. Always return valid JSON only. Never return empty arrays or empty strings."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        result_text = response.choices[0].message.content.strip()
        print(f"DEBUG: Raw AI response for SEO: {result_text[:300]}...")
        
        # Extract JSON from response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        print(f"DEBUG: Extracted SEO JSON: {result_text}")
        
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as je:
            print(f"DEBUG: JSON decode error: {je}")
            print(f"DEBUG: Attempting to fix JSON...")
            # Try to find JSON-like structure
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)
                result = json.loads(result_text)
            else:
                raise je
        
        # Ensure meta_description doesn't exceed 150 chars
        meta_desc = result.get("meta_description", "").strip()
        if len(meta_desc) > 150:
            meta_desc = meta_desc[:147] + "..."
        
        seo_keywords = result.get("seo_keywords", [])
        if not isinstance(seo_keywords, list):
            seo_keywords = []
        
        slug_suggestion = result.get("slug_suggestion", "").strip()
        seo_title_result = result.get("seo_title", title).strip()
        
        print(f"DEBUG: Parsed SEO - title: {seo_title_result}, desc: {meta_desc[:50]}..., keywords: {seo_keywords}, slug: {slug_suggestion}")
        
        return {
            "seo_title": seo_title_result if seo_title_result else title,
            "meta_description": meta_desc,
            "seo_keywords": seo_keywords[:6] if seo_keywords else [],  # Ensure max 6 keywords
            "slug_suggestion": slug_suggestion
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating SEO metadata: {e}")
        
        # Check for quota/billing errors
        if "quota" in error_msg.lower() or "429" in error_msg or "insufficient_quota" in error_msg.lower():
            print("ERROR: OpenAI API quota exceeded. Please add credits to your OpenAI account.")
        
        import traceback
        traceback.print_exc()
        return {
            "seo_title": title,
            "meta_description": "",
            "seo_keywords": [],
            "slug_suggestion": "",
            "error": "OpenAI API quota exceeded. Please check your billing."
        }

