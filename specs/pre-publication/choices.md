# Pre-publication decisions

- **Prove the index before trusting it.** The Git consumer route installs from a
  checkout, so it cannot catch a dependency range that only an index resolver
  would reject. A local PEP 503 index built from the real distributions proves
  resolution and install order without publishing anything.
- **Read the file people already have.** The declaration model is precise but
  costs a transcription. An importer that converts an existing document into the
  tool's own model removes that cost without widening any check's claim, and it
  needs no new dependency.
- **One entrance per reader, one promise per distribution.** A reader with one
  chart installs `chartgx`; a reader adopting the family installs `gxkit` and
  gets every tool. Slimming the umbrella behind extras was rejected: it would
  break the flagship "one entry point for the whole family" promise for exactly
  the readers it is meant to serve, and install weight is a smaller problem than
  a route that silently cannot inspect what it detected. Revisit only with
  adoption data showing the family route is the common case.
- **Publish the contract, not the prose.** Integrators branch on codes, exit
  codes and JSON keys. Saying so explicitly is what makes a v1.0 claim honest,
  and it costs one document.
