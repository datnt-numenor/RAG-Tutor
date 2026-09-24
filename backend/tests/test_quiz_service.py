from app.services.quiz_service import QuizService


def test_duplicate_text_detects_near_duplicate_questions():
    assert QuizService._is_duplicate_text(
        "TCP khác UDP như thế nào?",
        "TCP khác với UDP như thế nào?",
    )


def test_duplicate_text_keeps_different_questions():
    assert not QuizService._is_duplicate_text(
        "TCP khác UDP như thế nào?",
        "Địa chỉ IP dùng để làm gì trong mạng?",
    )
