"""Driver identity matching service."""

from typing import Optional, Tuple

import numpy as np

from database import driver_repository
from utils.logger import get_logger

logger = get_logger(__name__)


class DriverIdentityService:
    """Class-based driver identity matcher."""

    RECOGNITION_THRESHOLD = 0.45

    @staticmethod
    def _cosine_score(a: np.ndarray, b: np.ndarray) -> float:
        an = np.linalg.norm(a) + 1e-10
        bn = np.linalg.norm(b) + 1e-10
        return float(np.dot(a, b) / (an * bn))

    @classmethod
    def match(
        cls,
        embedding: Optional[np.ndarray] = None,
        embedding_2d: Optional[np.ndarray] = None,
        embedding_3d: Optional[np.ndarray] = None,
        driver_id: Optional[str] = None,
    ) -> Tuple[Optional[dict], float]:
        emb_2d = embedding_2d if embedding_2d is not None else embedding
        emb_2d = np.asarray(emb_2d, dtype=np.float32) if emb_2d is not None else None
        emb_3d = np.asarray(embedding_3d, dtype=np.float32) if embedding_3d is not None else None

        if driver_id:
            driver = driver_repository.get_driver_by_id(driver_id)
            if not driver:
                logger.debug("No driver found for id=%s", driver_id)
                return None, -1.0
            stored_3d = driver.get("face_embedding_3d")
            stored_2d = driver.get("face_embedding")
            if stored_3d and emb_3d is not None:
                db_emb = np.array(stored_3d, dtype=np.float32)
                score = cls._cosine_score(emb_3d, db_emb)
            elif stored_2d and emb_2d is not None:
                db_emb = np.array(stored_2d, dtype=np.float32)
                score = cls._cosine_score(emb_2d, db_emb)
            else:
                return None, -1.0
            return (driver if score >= cls.RECOGNITION_THRESHOLD else None), score

        best_driver = None
        best_score = -1.0
        for driver in driver_repository.get_all_drivers():
            stored_3d = driver.get("face_embedding_3d")
            stored_2d = driver.get("face_embedding")
            score = -1.0
            if stored_3d and emb_3d is not None:
                db_emb = np.array(stored_3d, dtype=np.float32)
                score = cls._cosine_score(emb_3d, db_emb)
            elif stored_2d and emb_2d is not None:
                db_emb = np.array(stored_2d, dtype=np.float32)
                score = cls._cosine_score(emb_2d, db_emb)
            if score > best_score:
                best_score = score
                best_driver = driver

        if best_driver is None or best_score < cls.RECOGNITION_THRESHOLD:
            logger.debug("No match above threshold (best=%.3f, threshold=%.2f)", best_score, cls.RECOGNITION_THRESHOLD)
            return None, best_score if best_driver is None else best_score
        logger.info("Driver matched: %s (score=%.3f)", best_driver.get("driver_id"), best_score)
        return best_driver, best_score


def match_embedding_to_driver(
    embedding: Optional[np.ndarray] = None,
    embedding_2d: Optional[np.ndarray] = None,
    embedding_3d: Optional[np.ndarray] = None,
    driver_id: Optional[str] = None,
) -> Tuple[Optional[dict], float]:
    """Compatibility function wrapper."""
    return DriverIdentityService.match(
        embedding=embedding,
        embedding_2d=embedding_2d,
        embedding_3d=embedding_3d,
        driver_id=driver_id,
    )

