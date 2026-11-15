"""Policy engine: batch facts -> the matching row of the response matrix (§8.5) -> actions.

The first rule whose condition holds wins (rules are ordered from most to least specific).
The engine only decides *what* should happen; guardrails execute the automatic actions and
humans own the rest.
"""

from dataclasses import dataclass, field

from src.response.settings import Action, PolicyConfig, Rule


@dataclass(frozen=True)
class PolicyFacts:
    """What the policy looks at for one batch."""

    diagnosis: str
    batch_level: int
    output_level: int  # highest level among L3/L4 alerts


@dataclass
class PolicyDecision:
    """Matched rule and the actions it requires."""

    rule_id: str
    situation: str
    actions: list[Action] = field(default_factory=list)

    def codes(self, mode: str | None = None) -> list[str]:
        """Action codes, optionally only the automatic or the human ones."""
        return [a.code for a in self.actions if mode is None or a.mode == mode]

    @property
    def wants_conservative(self) -> bool:
        """Whether this batch asks for the conservative mode (A4)."""
        return "A4" in self.codes("auto")

    @property
    def wants_quarantine(self) -> bool:
        """Whether this batch must be held for review (A2)."""
        return "A2" in self.codes("auto")


def matches(rule: Rule, facts: PolicyFacts) -> bool:
    """Whether every condition of the rule holds."""
    w = rule.when
    return (
        (w.diagnosis is None or facts.diagnosis in w.diagnosis)
        and (w.output_min_level is None or facts.output_level >= w.output_min_level)
        and (w.batch_min_level is None or facts.batch_level >= w.batch_min_level)
    )


def output_level(levels: dict[str, int], policy: PolicyConfig) -> int:
    """Highest alert level among the L3/L4 alerts that can change the credit policy."""
    return max((levels.get(a, 0) for a in policy.output_alerts), default=0)


def decide(facts: PolicyFacts, policy: PolicyConfig) -> PolicyDecision:
    """First matching rule of the matrix."""
    rule = next(r for r in policy.rules if matches(r, facts))
    return PolicyDecision(rule.id, rule.situation, list(rule.actions))
