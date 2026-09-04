"""Throwaway smoke test for the V20.2 CrewAI + Open Interpreter path."""
import sys
import time

from glados_skills.crew_orchestrator import run_crew


def _think(phase, message):
    print(f"[THINK:{phase}] {message}")


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else (
        "Respond with a single one-sentence GLaDOS-style greeting. Do NOT run any code."
    )
    print(f"=== run_crew({task!r}) ===")
    t0 = time.time()
    out = run_crew(task, think_fn=_think)
    print(f"\n=== RESULT ({time.time() - t0:.1f}s) ===")
    print(out)
    print("=== SMOKE_DONE ===")
