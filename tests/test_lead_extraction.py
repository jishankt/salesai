from services.lead_extraction import (
    extract_lead_signals,
    looks_like_product_question,
    is_valid_name,
)


def test_extract_name_explicit():
    signals = extract_lead_signals("hi my name is Salman")
    assert signals.get("name") == "Salman"


def test_extract_contact_phone():
    signals = extract_lead_signals("you can reach me at 0501234567")
    assert signals.get("contact", "").replace(" ", "") == "0501234567"


def test_extract_budget():
    signals = extract_lead_signals("looking for something around 500 AED")
    assert "500" in signals.get("budget", "")


def test_looks_like_product_question_positive():
    assert looks_like_product_question("do you have matte black ink?")
    assert looks_like_product_question("how much is the canvas roll")


def test_looks_like_product_question_confirmation_is_not_a_question():
    assert not looks_like_product_question("yes")
    assert not looks_like_product_question("go ahead")


def test_is_valid_name_rejects_stopwords_and_numbers():
    assert not is_valid_name("ink")
    assert not is_valid_name("yes")
    assert not is_valid_name("abc123")
    assert is_valid_name("Salman")
