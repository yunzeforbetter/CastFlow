# Jev module

Optional. Cold start copies this directory to `.castflow-runtime/jev/` only
when the Jev checkbox is on.

Put `TYPESAFE_API_KEY=...` in `.castflow-runtime/secrets.env`. That file is
the only secret store: later keys are more lines in the same file, read
through `manager.envfile`. It is gitignored. Do not put keys in
`config.json` or in this source tree.

Without the module directory, or without a key, package marking uses the
structural prior and prints that Jev is not configured.
