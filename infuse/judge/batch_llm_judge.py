#!/usr/bin/env python3
"""
Batch LLM Judge Evaluation Script

Loops through all trajectory files in results/attack_task and runs both:
1. LLM Judge for attack evaluation (attack success)
2. Benign Task LLM Judge for benign task evaluation (task completion)

Extracts existing evaluation information from trajectories and saves results
to JSON files alongside the trajectory files.
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import defaultdict

# Add parent directory to path

from infuse.evaluators.llm_evaluator import LLMJudgeEvaluator, BenignTaskLLMJudgeEvaluator
from infuse.tasks.task_suite import ExecutionTrace, SurfaceEvent, SurfaceType


def load_attack_templates(attacks_dir: str = "attacks") -> Dict[str, dict]:
    """Load attack info from attacks/ folder, indexed by attack_id.

    Reads each attack_*/config.toml and extracts attack_id, security_violation,
    and attacker_goal (from attack.description).

    Args:
        attacks_dir: Path to attacks directory (relative to project root)

    Returns:
        Dictionary mapping attack_id (as string) to attack info dict
    """
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    from infuse.paths import ATTACKS_DIR
    attacks_path = ATTACKS_DIR if attacks_dir in (None, "attacks", "benchmark/attacks") else Path(attacks_dir)
    if not attacks_path.exists():
        return {}

    templates = {}
    for toml_file in sorted(attacks_path.glob("attack_*/config.toml")):
        try:
            data = tomllib.loads(toml_file.read_text())
            attack = data.get("attack", {})
            attack_id = str(attack.get("id", ""))
            if not attack_id:
                continue
            templates[attack_id] = {
                "id": attack_id,
                "attacker_goal": attack.get("description", "").strip(),
                "security_violation": attack.get("metadata", {}).get("security_violation", ""),
            }
        except Exception:
            pass
    return templates


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)


def extract_existing_evaluation(traj_data: dict) -> Dict[str, Any]:
    """
    Extract existing evaluation information from trajectory JSON.
    
    Args:
        traj_data: Trajectory JSON data
        
    Returns:
        Dictionary with existing evaluation info
    """
    info = traj_data.get("info", {})
    
    existing_eval = {
        "attack_evaluation": info.get("evaluation", {}),
        "benign_evaluation": info.get("benign_evaluation", {}),
        "trace_info": info.get("trace", {}),
        "attack_events": info.get("attack_events", []),
        "attack_summary": info.get("attack_summary", {}),
    }
    
    return existing_eval


def extract_trajectory_info(traj_data: dict, attack_templates: Optional[Dict[str, dict]] = None) -> Dict[str, Any]:
    """
    Extract key information from trajectory for evaluation.

    Args:
        traj_data: Trajectory JSON data
        attack_templates: Optional dict mapping attack_id to attack template

    Returns:
        Dictionary with trajectory info
    """
    info = traj_data.get("info", {})
    task_entry = info.get("task_entry", {})
    attack_injection = info.get("attack_injection", {})

    # Get attack info from attack_injection (primary) or fallback to config
    attack_id = attack_injection.get("attack_id") or info.get("config", {}).get("agent", {}).get("attack_id")
    security_violation = attack_injection.get("attack_security_violation", "")

    # Look up attacker_goal from templates using attack_id
    attacker_goal = ""
    if attack_id and attack_templates:
        template = attack_templates.get(str(attack_id), {})
        attacker_goal = template.get("attacker_goal", "")

    return {
        "legitimate_objective": task_entry.get("intent", task_entry.get("prompt_example", "")),
        "attacker_goal": attacker_goal,
        "task_objective": task_entry.get("prompt_example", task_entry.get("user_goal", "")),
        "user_intent": task_entry.get("user_goal", task_entry.get("intent", "")),
        "security_violation": security_violation,
        "attack_id": attack_id,
        "task_id": task_entry.get("id", task_entry.get("task_id", "")),
        "exit_status": info.get("exit_status", ""),
        "model_name": info.get("config", {}).get("model", {}).get("model_name", "unknown"),
    }


def parse_trajectory_path(traj_path: Path, base_path: Path) -> Dict[str, Any]:
    """
    Parse trajectory path to extract attack_id, benign_task_id, model, and filename.
    
    Path structure: attack_task/{attack_id}/{benign_task_id}/{model}/{filename}.traj.json
    
    Args:
        traj_path: Full path to trajectory file
        base_path: Base path (e.g., results/attack_task)
        
    Returns:
        Dictionary with parsed path components
    """
    try:
        rel_path = traj_path.relative_to(base_path)
        parts = rel_path.parts
        
        if len(parts) >= 4:
            attack_id = parts[0]
            benign_task_id = parts[1]
            model = parts[2]
            filename = parts[3]
            
            return {
                "attack_id": attack_id,
                "benign_task_id": benign_task_id,
                "model": model,
                "filename": filename,
                "traj_basename": filename.replace(".traj.json", ""),
            }
        else:
            logger.warning(f"Unexpected path structure: {rel_path}")
            return {
                "attack_id": "unknown",
                "benign_task_id": "unknown",
                "model": "unknown",
                "filename": traj_path.name,
                "traj_basename": traj_path.stem.replace(".traj", ""),
            }
    except Exception as e:
        logger.error(f"Error parsing path {traj_path}: {e}")
        return {
            "attack_id": "unknown",
            "benign_task_id": "unknown",
            "model": "unknown",
            "filename": traj_path.name,
            "traj_basename": traj_path.stem.replace(".traj", ""),
        }


def evaluate_trajectory(
    traj_path: Path,
    judge_model: str = "gpt-4o-mini",
    skip_existing: bool = False,
    attack_templates: Optional[Dict[str, dict]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a single trajectory using both LLM judges.

    Args:
        traj_path: Path to trajectory JSON file
        judge_model: Model to use for judging
        skip_existing: If True, skip if evaluation files already exist
        attack_templates: Optional dict mapping attack_id to attack template

    Returns:
        Dictionary with evaluation results
    """
    logger.info(f"Evaluating: {traj_path}")

    # Load trajectory
    try:
        with open(traj_path, 'r') as f:
            traj_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load trajectory {traj_path}: {e}")
        return {"error": str(e), "traj_path": str(traj_path)}

    # Extract trajectory info
    traj_info = extract_trajectory_info(traj_data, attack_templates)
    existing_eval = extract_existing_evaluation(traj_data)
    
    # Parse path to get IDs
    base_path = traj_path.parent.parent.parent.parent  # Go up to attack_task/
    path_info = parse_trajectory_path(traj_path, base_path)
    
    # Determine output paths
    traj_dir = traj_path.parent
    traj_basename = path_info["traj_basename"]
    attack_judge_path = traj_dir / f"{traj_basename}.llm_judge.json"
    benign_judge_path = traj_dir / f"{traj_basename}.benign_llm_judge.json"
    
    # Skip if files exist and skip_existing is True
    if skip_existing and attack_judge_path.exists() and benign_judge_path.exists():
        logger.info(f"  Skipping (evaluation files already exist)")
        return {
            "traj_path": str(traj_path),
            "skipped": True,
            "attack_judge_path": str(attack_judge_path),
            "benign_judge_path": str(benign_judge_path),
        }
    
    results = {
        "traj_path": str(traj_path),
        "path_info": path_info,
        "traj_info": traj_info,
        "existing_evaluation": existing_eval,
    }
    
    # Run attack LLM judge
    logger.info(f"  Running attack LLM judge...")
    try:
        attack_evaluator = LLMJudgeEvaluator(judge_model=judge_model)
        
        # Try to get trace from trajectory (if available)
        # The evaluators prefer trajectory_file, but trace is still useful for fallback
        trace = None
        if "trace" in traj_data:
            trace_data = traj_data["trace"]
            if isinstance(trace_data, dict):
                # Try to reconstruct ExecutionTrace from dict
                try:
                    events = []
                    for event_dict in trace_data.get("events", []):
                        try:
                            surface_str = event_dict.get("surface", "TERMINAL_OUTPUT")
                            # Skip TERMINAL_INPUT if present (not a valid surface type)
                            if surface_str == "TERMINAL_INPUT":
                                continue
                            surface = SurfaceType(surface_str)
                            event = SurfaceEvent(
                                surface=surface,
                                content=event_dict.get("content", ""),
                                path=event_dict.get("path"),
                                step=event_dict.get("step", 0),
                                metadata=event_dict.get("metadata", {}),
                            )
                            events.append(event)
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Skipping invalid event: {e}")
                            pass  # Skip invalid events
                    
                    trace = ExecutionTrace(
                        task_id=str(traj_info.get("task_id", "unknown")),
                        events=events,
                        metadata=trace_data.get("metadata", {}),
                    )
                except Exception as e:
                    logger.debug(f"Could not reconstruct ExecutionTrace: {e}")
                    pass
        
        # Create minimal trace if needed (evaluators can work with None, but trace is better)
        if trace is None:
            trace = ExecutionTrace(
                task_id=str(traj_info.get("task_id", "unknown")),
                events=[],
                metadata={},
            )
        
        # Get workdir from trajectory (Docker cwd or default)
        workdir = "/work"  # Default for Docker
        env_config = traj_data.get("info", {}).get("config", {}).get("environment", {})
        if env_config:
            workdir = env_config.get("cwd", "/work")
        
        attack_result = attack_evaluator.evaluate(
            trace=trace,
            workdir=workdir,
            exit_status=traj_info.get("exit_status"),
            trajectory_file=str(traj_path),
            legitimate_objective=traj_info.get("legitimate_objective"),
            adversary_goal=traj_info.get("attacker_goal"),
        )
        
        attack_judge_result = {
            "trajectory_path": str(traj_path),
            "path_info": path_info,
            "trajectory_info": {
                "attack_id": traj_info.get("attack_id"),
                "benign_task_id": traj_info.get("task_id"),
                "legitimate_objective": traj_info.get("legitimate_objective"),
                "attacker_goal": traj_info.get("attacker_goal"),
                "security_violation": traj_info.get("security_violation"),
                "exit_status": traj_info.get("exit_status"),
            },
            "llm_judge": {
                "success": attack_result.success,
                "refused": attack_result.metadata.get("refused", False),
                "score": attack_result.score,
                "stdout": attack_result.stdout,
                "stderr": attack_result.stderr,
                "metadata": attack_result.metadata,
                "judge_model": judge_model,
            },
            "existing_evaluation": existing_eval.get("attack_evaluation", {}),
        }
        
        # Save attack judge result
        attack_judge_path.parent.mkdir(parents=True, exist_ok=True)
        with open(attack_judge_path, 'w') as f:
            json.dump(attack_judge_result, f, indent=2)
        
        results["attack_judge"] = attack_judge_result
        results["attack_judge_path"] = str(attack_judge_path)
        logger.info(f"  ✓ Attack judge: success={attack_judge_result['llm_judge']['success']}, score={attack_judge_result['llm_judge']['score']:.3f}")
        
    except Exception as e:
        logger.error(f"  ✗ Attack judge failed: {e}", exc_info=True)
        results["attack_judge_error"] = str(e)
    
    # Run benign task LLM judge
    logger.info(f"  Running benign task LLM judge...")
    try:
        benign_evaluator = BenignTaskLLMJudgeEvaluator(judge_model=judge_model)
        
        benign_result = benign_evaluator.evaluate(
            trace=trace,
            workdir=workdir,
            exit_status=traj_info.get("exit_status"),
            trajectory_file=str(traj_path),
            task_objective=traj_info.get("task_objective"),
            user_intent=traj_info.get("user_intent"),
        )
        
        benign_judge_result = {
            "trajectory_path": str(traj_path),
            "path_info": path_info,
            "trajectory_info": {
                "attack_id": traj_info.get("attack_id"),
                "benign_task_id": traj_info.get("task_id"),
                "task_objective": traj_info.get("task_objective"),
                "user_intent": traj_info.get("user_intent"),
                "exit_status": traj_info.get("exit_status"),
            },
            "benign_llm_judge": {
                "success": benign_result.success,
                "score": benign_result.score,
                "stdout": benign_result.stdout,
                "stderr": benign_result.stderr,
                "metadata": benign_result.metadata,
                "judge_model": judge_model,
            },
            "existing_evaluation": existing_eval.get("benign_evaluation", {}),
        }
        
        # Save benign judge result
        benign_judge_path.parent.mkdir(parents=True, exist_ok=True)
        with open(benign_judge_path, 'w') as f:
            json.dump(benign_judge_result, f, indent=2)
        
        results["benign_judge"] = benign_judge_result
        results["benign_judge_path"] = str(benign_judge_path)
        logger.info(f"  ✓ Benign judge: success={benign_judge_result['benign_llm_judge']['success']}, score={benign_judge_result['benign_llm_judge']['score']:.3f}")
        
    except Exception as e:
        logger.error(f"  ✗ Benign judge failed: {e}", exc_info=True)
        results["benign_judge_error"] = str(e)
    
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch LLM judge evaluation for attack task trajectories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate all trajectories
  python scripts/batch_llm_judge.py --trajectories-dir results/attack_task

  # Use specific judge model
  python scripts/batch_llm_judge.py --trajectories-dir results/attack_task --judge-model gpt-4

  # Skip existing evaluations
  python scripts/batch_llm_judge.py --trajectories-dir results/attack_task --skip-existing

  # Evaluate specific attack/benign task
  python scripts/batch_llm_judge.py --trajectories-dir results/attack_task --attack-id 6 --benign-task-id 12
        """
    )
    
    parser.add_argument(
        "--trajectories-dir",
        type=str,
        default="results/attack_task",
        help="Directory containing trajectory files (default: results/attack_task)"
    )
    
    parser.add_argument(
        "--judge-model",
        type=str,
        default="gpt-4o-mini",
        help="Model to use for judging (default: gpt-4o-mini)"
    )
    
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip trajectories that already have evaluation files"
    )
    
    parser.add_argument(
        "--attack-id",
        type=str,
        help="Filter by specific attack ID (e.g., '6')"
    )
    
    parser.add_argument(
        "--benign-task-id",
        type=str,
        help="Filter by specific benign task ID (e.g., '12')"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Filter by specific model name (e.g., 'gpt-4o-mini')"
    )
    
    parser.add_argument(
        "--output-summary",
        type=str,
        help="Path to save summary JSON file with all results"
    )
    
    args = parser.parse_args()
    
    # Find all trajectory files
    trajectories_dir = Path(args.trajectories_dir)
    if not trajectories_dir.exists():
        logger.error(f"Trajectories directory not found: {trajectories_dir}")
        sys.exit(1)
    
    # Find all .traj.json files
    traj_files = list(trajectories_dir.rglob("*.traj.json"))
    
    if not traj_files:
        logger.warning(f"No trajectory files found in {trajectories_dir}")
        sys.exit(0)
    
    logger.info(f"Found {len(traj_files)} trajectory files")
    
    # Filter by attack_id, benign_task_id, model if specified
    if args.attack_id or args.benign_task_id or args.model:
        filtered_files = []
        for traj_file in traj_files:
            rel_path = traj_file.relative_to(trajectories_dir)
            parts = rel_path.parts
            
            if len(parts) >= 4:
                attack_id = parts[0]
                benign_task_id = parts[1]
                model = parts[2]
                
                match = True
                if args.attack_id and attack_id != args.attack_id:
                    match = False
                if args.benign_task_id and benign_task_id != args.benign_task_id:
                    match = False
                if args.model and model != args.model:
                    match = False
                
                if match:
                    filtered_files.append(traj_file)
        
        traj_files = filtered_files
        logger.info(f"Filtered to {len(traj_files)} trajectory files")
    
    if not traj_files:
        logger.warning("No trajectory files match the filters")
        sys.exit(0)

    # Load attack templates once
    attack_templates = load_attack_templates()
    if attack_templates:
        logger.info(f"Loaded {len(attack_templates)} attack templates")

    # Evaluate each trajectory
    all_results = []
    success_count = 0
    error_count = 0
    skipped_count = 0
    total_cost = 0.0

    for i, traj_file in enumerate(sorted(traj_files), 1):
        logger.info(f"\n[{i}/{len(traj_files)}] Processing: {traj_file.relative_to(trajectories_dir)}")

        try:
            result = evaluate_trajectory(
                traj_file,
                judge_model=args.judge_model,
                skip_existing=args.skip_existing,
                attack_templates=attack_templates,
            )

            if result.get("skipped"):
                skipped_count += 1
            elif "error" in result:
                error_count += 1
            else:
                success_count += 1
                # Extract costs from both judges
                attack_cost = result.get("attack_judge", {}).get("llm_judge", {}).get("metadata", {}).get("cost", 0.0) or 0.0
                benign_cost = result.get("benign_judge", {}).get("benign_llm_judge", {}).get("metadata", {}).get("cost", 0.0) or 0.0
                eval_cost = attack_cost + benign_cost
                total_cost += eval_cost
                logger.info(f"  💰 Cost: ${eval_cost:.6f} (Total so far: ${total_cost:.6f})")

            all_results.append(result)

        except Exception as e:
            logger.error(f"Failed to evaluate {traj_file}: {e}", exc_info=True)
            error_count += 1
            all_results.append({
                "traj_path": str(traj_file),
                "error": str(e),
            })
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total trajectories: {len(traj_files)}")
    logger.info(f"  ✓ Successfully evaluated: {success_count}")
    logger.info(f"  ⊘ Skipped (existing): {skipped_count}")
    logger.info(f"  ✗ Errors: {error_count}")
    logger.info(f"  💰 Total cost: ${total_cost:.6f}")
    logger.info("=" * 60)
    
    # Save summary if requested
    if args.output_summary:
        summary_path = Path(args.output_summary)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            "total_trajectories": len(traj_files),
            "successful": success_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total_cost": total_cost,
            "judge_model": args.judge_model,
            "results": all_results,
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    main()


