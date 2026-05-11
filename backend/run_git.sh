#!/bin/bash
git add app/routers/tasks.py app/services/github_service.py app/services/clod_service.py app/models/state.py
git commit -m "feat(backend): implement self-healing pipeline, model escalation, and PR reuse"
git push origin HEAD
