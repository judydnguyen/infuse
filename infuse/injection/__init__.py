"""Build-time payload injection (the only injection path in the benchmark).

    spec  = AttackSpec.load(1)              # benchmark/attacks/attack_1/config.toml
    task  = TaskSurfaces.load("task_1")     # benchmark/tasks/task_1/.../benign.toml
    rec   = inject(spec, task, workdir)     # writes files, returns an InjectionRecord
"""
from infuse.injection.assemble import assemble_payload, payload_sha256, variant_template
from infuse.injection.injector import InjectionRecord, inject, plan
from infuse.injection.resolver import Candidate, resolve, select
from infuse.injection.spec import AttackSpec, SpecError, TaskSurfaces

__all__ = ["AttackSpec", "TaskSurfaces", "SpecError", "Candidate", "resolve", "select", "inject", "plan",
           "InjectionRecord", "assemble_payload", "variant_template", "payload_sha256"]
