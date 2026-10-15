# Guards that detect broken subjects

Retire A10. Validate the actual README setup-prompt block and the install command
it directs an agent to follow; a surviving unrelated link is not a prompt.
Extract executable coverage arguments from the shell/CI run steps, ignoring
comments and quoted echo text. The complete coverage membership/floor invariant
must refer to a pytest invocation that actually executes.

Run mutation drills on temporary copies: delete prompt, corrupt command, lower
the floor but leave its old text in a comment, omit a tool, and restore the old
production gate/converter/math defects. The named regression must fail for the
expected assertion, not collection or environment errors. Wire the bounded
mutation runner into local and CI gates so future proofs are executable.

Checkpoint: live gates accept the real tree and reject every intended mutant;
no test writes to a user's real tool directory or leaves processes running.
