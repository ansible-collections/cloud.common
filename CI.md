# Continuous Integration (CI)

## Cloud Common Collection Testing

GitHub Actions are used to run the CI for the cloud.common collection. The workflows used for the CI can be found in the [.github/workflows](.github/workflows) directory.

### PR Testing Workflows

The following tests run on every pull request:

| Job | Description | Python Versions | ansible-core Versions |
| --- | ----------- | --------------- | --------------------- |
| [Changelog](.github/workflows/changelog.yaml) | Checks for the presence of changelog fragments | 3.12 | devel |
| [Linters](.github/workflows/linters.yaml) | Runs `black`, `flake8`, `isort`, and `flynt` on plugins and tests | 3.10 | devel |
| [Sanity](.github/workflows/sanity-tests.yaml) | Runs ansible sanity checks | See compatibility table below | stable-2.16, stable-2.17, stable-2.18, stable-2.20, stable-2.21 |
| [Unit tests](.github/workflows/unit-tests.yaml) | Executes unit test cases | See compatibility table below | stable-2.16, stable-2.17, stable-2.18, stable-2.20, stable-2.21 |
| [Integration](.github/workflows/integration-tests.yaml) | Executes integration test suites for turbo module functionality | 3.10, 3.11, 3.12 | stable-2.17, stable-2.18 |
| [Integration (kubernetes.core)](.github/workflows/integration-tests-kubernetes-core.yaml) | Runs the kubernetes.core integration targets with turbo mode enabled | 3.13 (milestone), 3.10 - 3.12 (stable-2.17) | milestone, stable-2.17 |

**Note:** Integration tests validate the turbo module daemon and standalone execution modes.

### Python Version Compatibility by ansible-core Version

These are enforced through the `matrix_exclude` settings in the sanity and unit test GitHub Actions workflows.

| ansible-core Version | Sanity Tests | Unit Tests |
| -------------------- | ------------ | ---------- |
| stable-2.21 | 3.12, 3.13, 3.14 | 3.12, 3.13, 3.14 |
| stable-2.20 | 3.12, 3.13, 3.14 | 3.12, 3.13, 3.14 |
| stable-2.18 | 3.11, 3.12, 3.13 | 3.11, 3.12, 3.13 |
| stable-2.17 | 3.10, 3.11, 3.12 | 3.10, 3.11, 3.12 |
| stable-2.16 | 3.10, 3.11 | 3.10, 3.11 |
