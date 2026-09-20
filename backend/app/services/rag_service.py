from google import genai
from app.services.embedding_service import EmbeddingService


class RAGService:
    def __init__(self, supabase, gemini_api_key):
        self.supabase = supabase
        self.embedding_service = EmbeddingService()

        self.gemini_client = genai.Client(
            api_key=gemini_api_key
        )

    def retrieve(
        self,
        project_id: str,
        query: str,
        top_k: int = 3,
        threshold: float = 0.3
    ) -> list[dict]:

        query_embedding = self.embedding_service.embed(query)

        response = self.supabase.rpc(
            "match_rag_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "match_threshold": threshold
            }
        ).execute()

        return response.data

    def build_context(self, results: list[dict]) -> str:
        context_parts = []

        for result in results:
            context_parts.append(result["content"])

        return "\n\n".join(context_parts)

    def build_prompt(
        self,
        question: str,
        context: str
    ) -> str:
      return f"""
    Bạn là trợ lý trả lời câu hỏi dựa trên context được cung cấp.

    Context:
    {context}

    Question:
    {question}

    Yêu cầu:
    - Chỉ trả lời dựa trên context.
    - Không tự thêm thông tin bên ngoài context.
    - Nếu context không đủ thông tin, hãy trả lời:
      "Không đủ thông tin trong tài liệu để trả lời câu hỏi này."
    """     

    def generate_answer(
        self,
        question: str,
        context: str
    ) -> str:

        prompt = self.build_prompt(
            question=question,
            context=context
        )

        interaction = self.gemini_client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt
        )

        return interaction.output_text

    def build_sources(self, results: list[dict]) -> list[dict]:
      sources = []
      seen = set()

      for result in results:
          key = (
              result["source_file"],
              result["page"]
          )

          if key in seen:
              continue

          seen.add(key)

          sources.append({
              "source_file": result["source_file"],
              "page": result["page"]
          })

      return sources

    def answer(
        self,
        project_id: str,
        question: str,
        top_k: int = 3,
        threshold: float = 0.3
    ) -> dict:

        results = self.retrieve(
            query=question,
            top_k=top_k,
            threshold=threshold
        )

        if not results:
            return {
                "answer": "Không đủ thông tin trong tài liệu để trả lời câu hỏi này.",
                "sources": []
            }

        context = self.build_context(results)

        answer = self.generate_answer(
            question=question,
            context=context
        )

        sources = self.build_sources(results)

        return {
            "answer": answer,
            "sources": sources
        }
          