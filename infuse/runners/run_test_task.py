#!/usr/bin/env python3
"""
Runner for test_tasks structure.

Thin wrapper that delegates to run_single_test_with_minisweagent, which handles:
1. Running setup.sh (with setup_args from task.toml)
2. Building Docker image from task-specific Dockerfile
3. Applying attack injection by manipulating files directly
4. Running task in Docker container
5. Collecting trajectory and evaluating
6. Running clean.sh after execution (always, via finally block)
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directory to path

from infuse.paths import TASKS_DIR
from infuse.runners.run_single_minisweagent import run_single_test_with_minisweagent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from infuse.registry import DEFENSE_NAMES, build_defense, agent_model_config


def run_test_task(
    task_id: str,
    attack_id: Optional[str] = None,
    model_name: str = "gpt-4",
    model_class: Optional[str] = None,
    tasks_root: Optional[str] = None,
    output_dir: Optional[str] = None,
    use_docker: bool = True,
    timeout_seconds: Optional[int] = None,
    cost_limit: Optional[float] = None,
    attack_overrides: Optional[Dict[str, Any]] = None,
    defense_name: Optional[str] = None,
    defense_model: Optional[str] = None,
    overwrite: bool = False,
    obs_level: str = "default",
    resolution_strategy: str = "task_order",
    run_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run a test task by delegating to run_single_test_with_minisweagent.

    This function handles loading the attack config and then delegates all
    execution (setup, Docker build, agent run, cleanup) to the minisweagent runner.

    Args:
        task_id: Task identifier (e.g., "task_1")
        attack_id: Optional attack identifier (e.g., "1")
        model_name: Model name to use
        model_class: Model class (e.g., "anthropic", "litellm", "openrouter")
        tasks_root: Root directory for test_tasks (defaults to ./test_tasks)
        output_dir: Output directory for results
        use_docker: Whether to use Docker
        timeout_seconds: Timeout in seconds
        cost_limit: Cost limit in USD

    Returns:
        Dictionary with execution results
    """
    # Setup paths
    if tasks_root is None:
        tasks_root_path = TASKS_DIR
    else:
        tasks_root_path = Path(tasks_root)

    if output_dir is None:
        from infuse.paths import results_dir
        output_dir = str(results_dir())

    logger.info(f"Running test task {task_id}")
    logger.info(f"Tasks root: {tasks_root_path}")
    logger.info(f"Output dir: {output_dir}")

    # Load attack config if provided
    attack_config = None
    if attack_id and attack_id.lower() != "none":
        from infuse.injection import AttackSpec
        attack_config = AttackSpec.load(attack_id, strict=False).raw
        logger.info(f"Loaded attack config: {attack_config.get('attack', {}).get('name', 'Unknown')}")

    # Model + defense come from the registries (benchmark/configs/models.yaml, infuse.registry.defenses)
    model_name, model_config = agent_model_config(model_name, model_class)

    agent_config: Dict[str, Any] = {}
    if defense_name and defense_name.lower() not in ("none", ""):
        defense = build_defense(defense_name, defense_model)
        agent_config["_defense"] = defense
        logger.info(f"Defense: {defense}")

    # Delegate everything to run_single_test_with_minisweagent
    # It handles: setup.sh -> Docker build -> agent run -> clean.sh
    print(f"Running task with model_name={model_name}, model_config={model_config}, use_docker={use_docker}, timeout_seconds={timeout_seconds}, cost_limit={cost_limit}", file=sys.stderr)
    print(f"Attack config: {attack_config}", file=sys.stderr)
    result = run_single_test_with_minisweagent(
        task_id=task_id,
        model_name=model_name,
        model_config=model_config,
        agent_config=agent_config or None,
        output_dir=output_dir,
        timeout_seconds=timeout_seconds,
        cost_limit=cost_limit,
        use_docker=use_docker,
        attack_config=attack_config,
        task_dir=str(tasks_root_path),
        attack_overrides=attack_overrides,
        defense_name=defense_name,
        overwrite=overwrite,
        obs_level=obs_level,
        resolution_strategy=resolution_strategy,
        run_metadata=run_metadata,
    )

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run a test task with new environment population flow")

    parser.add_argument("--task-id", required=True, help="Task identifier (e.g., task_1)")
    parser.add_argument("--attack-id", help="Attack identifier (e.g., 1)")
    parser.add_argument("--model", default="gpt-4", help="Model name")
    parser.add_argument("--model-class", help="Model class (e.g., anthropic, litellm, openrouter)")
    parser.add_argument("--tasks-root", help="Root directory for test_tasks")
    parser.add_argument("--output-dir", default="./results", help="Output directory")
    parser.add_argument("--no-docker", action="store_true", help="Don't use Docker")
    parser.add_argument("--overwrite", action="store_true", help="Re-run even if trajectory already exists")
    parser.add_argument("--timeout", type=int, help="Timeout in seconds")
    parser.add_argument("--cost-limit", type=float, help="Cost limit in USD")
    parser.add_argument("--attack-overrides", type=json.loads, default=None, metavar="JSON",
                        help='JSON dict overriding attack config fields, e.g. \'{"inject_prefix": "...", "inject_position": "append"}\'')
    parser.add_argument(
        "--defense",
        default=None,
        choices=DEFENSE_NAMES,
        metavar="DEFENSE",
        help=(
            "Observation-level defense to apply. "
            f"Choices: {', '.join(DEFENSE_NAMES)}. "
            "LLM-based defenses (input_filter, input_transform, output_filter, pipeline) "
            "require --defense-model."
        ),
    )
    parser.add_argument(
        "--defense-model",
        default=None,
        metavar="MODEL",
        help="Model name to use as the LLM judge/rewriter for LLM-based defenses.",
    )

    args = parser.parse_args()

    try:
        result = run_test_task(
            task_id=args.task_id,
            attack_id=args.attack_id,
            model_name=args.model,
            model_class=args.model_class,
            tasks_root=args.tasks_root,
            output_dir=args.output_dir,
            use_docker=not args.no_docker,
            overwrite=args.overwrite,
            timeout_seconds=args.timeout,
            cost_limit=args.cost_limit,
            attack_overrides=args.attack_overrides,
            defense_name=args.defense,
            defense_model=args.defense_model,
        )

        print(json.dumps(result, indent=2))
        return 0
    except Exception as e:
        logger.error(f"Error running task: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
