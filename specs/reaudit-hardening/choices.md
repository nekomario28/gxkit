- **A report must reach the console it is printed on.** A message that names what
  it found may contain a character the console's code page lacks. The CLI escapes
  unencodable characters instead of failing, because losing a verdict to an
  encoding error reports the wrong thing about the artifact.
- **One owner for that tolerance.** `gxcore.cli.run` reconfigures the streams; the
  umbrella does not repeat it, since every tool report passes through the shared
  CLI and the umbrella's own output is ASCII and stderr, which Python already
  escapes.
