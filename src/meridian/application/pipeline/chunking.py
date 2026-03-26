from typing import List
from src.meridian.domain.entities import Document, Chunk

def chunk_document(document: Document, chunk_size: int = 1500, overlap: int = 200) -> List[Chunk]:
    chunks = []
    text = document.content
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        if end < len(text):
            break_point = max(text.rfind('\n', start, end), text.rfind('. ', start, end))
            if break_point != -1 and break_point > start + (chunk_size // 2):
                end = break_point + 1
                
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                document_id=document.id,
                content=chunk_text,
                metadata={"source": document.source, "url": document.url, "title": document.title}
            ))
            
        start = end - overlap if end < len(text) else len(text)
        
    return chunks
