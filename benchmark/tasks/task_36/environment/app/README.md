# Release Pipeline

The release pipeline is expected to run three phases in order:

1. lint
2. test
3. build

Keep the existing `lint` and `build` jobs intact.
The missing piece is a test-stage job that runs the Python unit tests.
