import numpy as np
import pytest
from agentops_server.orchestrator.input_encoding import lexical_hash_vector


def test_lexical_hash_vector_is_deterministic_and_normalized() -> None:
    first = lexical_hash_vector("Graph neural networks for molecules")
    second = lexical_hash_vector("Graph neural networks for molecules")

    np.testing.assert_array_equal(first, second)
    assert first.shape == (128,)
    assert np.linalg.norm(first) == pytest.approx(1.0)


def test_lexical_hash_vector_normalizes_case_unicode_and_punctuation() -> None:
    np.testing.assert_array_equal(
        lexical_hash_vector("Ｃoncept, DRIFT!"),
        lexical_hash_vector("concept drift"),
    )


def test_lexical_hash_vector_reflects_token_overlap() -> None:
    baseline = lexical_hash_vector("graph neural networks for molecules")
    related = lexical_hash_vector("graph neural networks for proteins")
    unrelated = lexical_hash_vector("renaissance poetry translation")

    assert float(baseline @ related) > float(baseline @ unrelated)
    np.testing.assert_array_equal(lexical_hash_vector(""), np.zeros(128))


def test_lexical_hash_vector_rejects_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match="dimensions must be positive"):
        lexical_hash_vector("text", dimensions=0)
