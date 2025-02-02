import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from loguru import logger

MODEL_NAME = "jackaduma/SecBERT"
_tokenizer = None
_model = None


def get_tokenizer():
    """
    Loads the tokenizer for the specified model using a singleton pattern.
    """
    global _tokenizer
    if _tokenizer is None:
        logger.info(f"Loading tokenizer: {MODEL_NAME}")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _tokenizer


def get_model():
    """
    Loads the model for the specified model using a singleton pattern.
    """
    global _model
    if _model is None:
        logger.info(f"Loading model: {MODEL_NAME}")
        _model = AutoModel.from_pretrained(MODEL_NAME)
    return _model


def get_embedding(text: str) -> np.ndarray:
    """
    Returns the embedding (as a NumPy array) for the provided text using the "jackaduma/SecBERT" model.

    This function:
      - Tokenizes the input text.
      - Feeds it through the model to obtain the last hidden state.
      - Applies mean pooling (taking into account the attention mask) to generate a fixed-size sentence embedding.

    Args:
        text (str): The input text for which to generate an embedding.

    Returns:
        np.ndarray: The resulting sentence embedding.
    """
    tokenizer = get_tokenizer()
    model = get_model()
    if not text:
        text = ""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state
    attention_mask = inputs["attention_mask"]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
    sum_embeddings = torch.sum(embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    mean_embeddings = sum_embeddings / sum_mask

    return mean_embeddings[0].cpu().numpy()


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Computes the cosine similarity between two vectors (range: -1 to 1).

    Args:
        vec_a (np.ndarray): First vector.
        vec_b (np.ndarray): Second vector.

    Returns:
        float: Cosine similarity score.
    """
    vec_a = vec_a.astype(np.float32)
    vec_b = vec_b.astype(np.float32)
    dot_val = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot_val / (norm_a * norm_b))
