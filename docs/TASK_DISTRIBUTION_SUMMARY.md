# Task Distribution Summary

This document summarizes the distribution of tasks in the `test_tasks` directory.

## Overview Statistics

- **Total Tasks**: 20
- **Difficulty Distribution**:
  - Easy: 4 tasks (20%)
  - Medium: 10 tasks (50%)
  - Hard: 6 tasks (30%)

## Task Distribution by Category

| Category | Count | Percentage | Task IDs |
|----------|-------|------------|----------|
| microservices | 2 | 10% | task_12, task_20 |
| security | 2 | 10% | task_8, task_9 |
| dependency_setups | 1 | 5% | task_3 |
| dependency_management | 1 | 5% | task_7 |
| unit_testing | 1 | 5% | task_5 |
| data_processing | 1 | 5% | task_6 |
| secure_file_handling | 1 | 5% | task_1 |
| archive_management | 1 | 5% | task_2 |
| model_evaluation | 1 | 5% | task_4 |
| system_monitoring | 1 | 5% | task_10 |
| web_performance | 1 | 5% | task_11 |
| file_organization | 1 | 5% | task_13 |
| image_processing | 1 | 5% | task_14 |
| documentation | 1 | 5% | task_15 |
| web_automation | 1 | 5% | task_16 |
| technical_writing | 1 | 5% | task_17 |
| bug_fixing | 1 | 5% | task_18 |
| database_migration | 1 | 5% | task_19 |

## Detailed Task Table

| Task ID | Category | Difficulty | Duration (min) | Expert Est. (min) | Junior Est. (min) | Key Tags |
|---------|----------|------------|---------------|-------------------|-------------------|----------|
| task_1 | secure_file_handling | medium | 15 | 5 | 20 | zip, filesystem, path-traversal, cli-agent |
| task_2 | archive_management | medium | 15 | 5 | 20 | archive, zip, tar, filesystem, cli-agent |
| task_3 | dependency_setups | easy | 15 | 5 | 20 | - |
| task_4 | model_evaluation | easy | 15 | 5 | 20 | pytorch, mnist, checkpoint, evaluation |
| task_5 | unit_testing | easy | 15 | 5 | 20 | pytest, testing, json |
| task_6 | data_processing | medium | 15 | 5 | 20 | csv, data, merge, pandas, python |
| task_7 | dependency_management | medium | 15 | 5 | 20 | python, dependencies, lockfile, requirements, pip |
| task_8 | security | medium | 15 | 5 | 20 | permissions, file-security, chmod, filesystem |
| task_9 | security | medium | 20 | 10 | 30 | cryptography, security, md5, sha1, random, secrets, hashlib, cli-agent |
| task_10 | system_monitoring | easy | 10 | 3 | 10 | disk-usage, json, filesystem, monitoring |
| task_11 | web_performance | hard | 30 | 15 | 45 | react, webpack, lighthouse, performance, optimization, code-splitting, bundle-size |
| task_12 | microservices | hard | 40 | 20 | 60 | docker-compose, microservices, timeout, circuit-breaker, retry, service-mesh, envoy, distributed-systems |
| task_13 | file_organization | medium | 15 | 5 | 20 | file-organization, duplicates, filesystem, cli-agent |
| task_14 | image_processing | medium | 15 | 5 | 20 | image-resize, image-compression, web-optimization, pillow, imagemagick, cli-agent |
| task_15 | documentation | medium | 15 | 5 | 20 | readme, documentation, python, code-analysis, cli-agent |
| task_16 | web_automation | hard | 30 | 15 | 45 | web-scraping, price-monitoring, automation, cron, beautifulsoup, selenium, cli-agent |
| task_17 | technical_writing | hard | 40 | 20 | 60 | openapi, swagger, api-documentation, sdk-generation, rest-api, technical-writing, cli-agent |
| task_18 | bug_fixing | medium | 20 | 10 | 30 | javascript, nodejs, authentication, debugging |
| task_19 | database_migration | hard | 40 | 20 | 60 | rails, postgresql, database, migration, microservices, data-extraction, cli-agent |
| task_20 | microservices | hard | 30 | 20 | 60 | docker, envoy, timeout, circuit-breaker, retry |

## Difficulty Distribution

| Difficulty | Count | Percentage | Task IDs |
|------------|-------|------------|----------|
| Easy | 4 | 20% | task_3, task_4, task_5, task_10 |
| Medium | 10 | 50% | task_1, task_2, task_6, task_7, task_8, task_9, task_13, task_14, task_15, task_18 |
| Hard | 6 | 30% | task_11, task_12, task_16, task_17, task_19, task_20 |

## Duration Distribution

| Duration Range | Count | Task IDs |
|----------------|-------|----------|
| 10 minutes | 1 | task_10 |
| 15 minutes | 13 | task_1, task_2, task_3, task_4, task_5, task_6, task_7, task_8, task_13, task_14, task_15 |
| 20 minutes | 2 | task_9, task_18 |
| 30 minutes | 3 | task_11, task_16, task_20 |
| 40 minutes | 2 | task_12, task_17, task_19 |

## Common Tags

The most frequently appearing tags across all tasks:

- **cli-agent**: 11 tasks (55%)
- **filesystem**: 5 tasks (25%)
- **python**: 3 tasks (15%)
- **docker**: 2 tasks (10%)
- **microservices**: 2 tasks (10%)
- **security**: 2 tasks (10%)
- **timeout**: 2 tasks (10%)
- **circuit-breaker**: 2 tasks (10%)
- **retry**: 2 tasks (10%)

## Resource Requirements

### CPU Distribution
- **2 CPUs**: 18 tasks (90%)
- **4 CPUs**: 2 tasks (10%) - task_11, task_12, task_20

### Memory Distribution
- **2GB**: 18 tasks (90%)
- **4GB**: 2 tasks (10%) - task_11, task_12, task_20

### Storage Distribution
- **1GB**: 15 tasks (75%)
- **2GB**: 4 tasks (20%) - task_11, task_14, task_17, task_19
- **5GB**: 1 task (5%) - task_12

## Cost Limits

| Cost Limit | Count | Task IDs |
|------------|-------|----------|
| $1.0 | 13 | task_1, task_2, task_3, task_4, task_5, task_6, task_7, task_8, task_10, task_13, task_14, task_15 |
| $1.5 | 2 | task_9, task_18 |
| $2.0 | 3 | task_11, task_16, task_20 |
| $2.5 | 2 | task_17, task_19 |
| $3.0 | 1 | task_12 |

## Max Steps Distribution

| Max Steps | Count | Task IDs |
|-----------|-------|----------|
| 20 | 13 | task_1, task_2, task_3, task_4, task_5, task_6, task_7, task_8, task_10 |
| 30 | 3 | task_13, task_14, task_15, task_18 |
| 40 | 2 | task_9, task_20 |
| 50 | 2 | task_11, task_16 |
| 60 | 3 | task_12, task_17, task_19 |

---

*Generated: 2026-02-19*
