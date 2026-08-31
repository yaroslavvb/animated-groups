# Repository status: superseded

- Do not start new development work in this repository. All future Animated Groups
  work is happening in the sibling `animated-groups-fable` repository, where the
  necessary functionality has been ported.
- If a request for Animated Groups work lands in this repository, stop and tell the
  user to switch the workspace to `animated-groups-fable` rather than implementing
  it here.
- Only make changes in this repository when the user explicitly asks to modify this
  legacy repository itself.

# Workspace boundary

- Do not inspect, edit, reset, clean, or run commands in the sibling
  `animated-groups-fable` directory from this workspace. Switch to that repository
  first so its own instructions and working tree are in scope.
- Only cross this boundary when the user explicitly overrides this instruction.

# Deployment default

- After completing requested changes and the relevant checks in this repository,
  commit and push the deployment branch automatically unless the user explicitly
  asks not to deploy.
