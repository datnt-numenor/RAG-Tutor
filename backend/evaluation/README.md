# RAG Evaluation

Dataset format: one JSON object per line.

Example:

    {"question":"Attention dùng những vector nào?","expected_document":"transformer.pdf","expected_page":2,"answer_keywords":["query","key","value"],"should_abstain":false}
    {"question":"Tác giả sinh năm bao nhiêu?","should_abstain":true}

Run from backend:

    python -m evaluation.run_rag_eval --project-id <PROJECT_UUID> --dataset evaluation/my_eval.jsonl --output evaluation/result.json

Reported metrics:

- retrieval hit rate
- citation hit rate
- abstain accuracy
- answer keyword coverage
- median retrieval latency
- median end-to-end latency

Use a fixed dataset for comparisons between embedding/chunking configurations.
