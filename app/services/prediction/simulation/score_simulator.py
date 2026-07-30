import random
from dataclasses import dataclass

from app.services.prediction.models.types import ScoreProbability


@dataclass(frozen=True)
class SimulatedScore:
    score: str
    occurrences: int
    average_probability: float
    rank: int


@dataclass(frozen=True)
class ScoreSimulationResult:
    simulations: int
    scores: list[SimulatedScore]
    low_confidence: bool


class ScoreSimulator:
    def __init__(self, simulations: int = 10_000) -> None:
        self._simulations = simulations

    def simulate(self, distribution: list[ScoreProbability], *, seed: str) -> ScoreSimulationResult:
        if not distribution:
            return ScoreSimulationResult(self._simulations, [], True)
        weighted = sorted(distribution, key=lambda item: item.probability, reverse=True)
        cumulative = []
        running = 0.0
        for item in weighted:
            running += item.probability
            cumulative.append((running, item))
        random_generator = random.Random(seed)
        counts: dict[str, int] = {item.score: 0 for item in weighted}
        probabilities = {item.score: item.probability for item in weighted}
        for _ in range(self._simulations):
            draw = random_generator.random()
            selected = cumulative[-1][1]
            for threshold, item in cumulative:
                if draw <= threshold:
                    selected = item
                    break
            counts[selected.score] += 1
        ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        scores = [
            SimulatedScore(
                score=score,
                occurrences=occurrences,
                average_probability=probabilities[score],
                rank=index,
            )
            for index, (score, occurrences) in enumerate(ranked[:10], start=1)
        ]
        top_probability = weighted[0].probability
        return ScoreSimulationResult(
            simulations=self._simulations,
            scores=scores,
            low_confidence=top_probability < 0.12,
        )
