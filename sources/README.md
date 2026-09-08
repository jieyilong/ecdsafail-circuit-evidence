# Circuit Sources and Frozen Tools

The [source-tree manifest](../provenance/source-trees.json) binds every browsable source file to its original archive. The original archives are unchanged. Browsable trees omit only cached Python bytecode, whose hashes are retained in that manifest. No code used by the Rust emitter or evaluator is omitted.

| Snapshot | Browse | Original source revision | Role |
|---|---|---|---|
| Original ping-pong | [Source](trees/original-pingpong/) | [2e0187c99fef](https://github.com/jieyilong/ecdsafail-challenge/tree/2e0187c99fef038f079aaf76b6d36f64cce7481e) | Original split-cleanup comparison circuit |
| Conservative ping-pong | [Source](trees/conservative-pingpong/) | `345c23fcf1073b7559a9d41e113f755259545bf2` | Frozen conservative circuit and auxiliary evaluator, preserved here as a source snapshot |
| Jump-2 | [Source](trees/jump2/) | [080452804328](https://github.com/jieyilong/ecdsafail-challenge/tree/080452804328698214f36655d95c9883be6a3080) | Lower-width split-cleanup comparison circuit |
| Zero-payload probe | [Source](trees/zero-payload-probe/) | Diagnostic overlay on `345c23fcf1073` | Post-hoc subroutine probe, not a promoted circuit |

The conservative commit was local to the original study. The archive and browsable tree provide its contents without assuming that commit exists in the upstream repository. The diagnostic snapshot modifies only its entry-point dispatch, module visibility, and reporting helper. Its arithmetic is the frozen arithmetic.

## Which Tool Should I Run?

- Use the current [reproduction wrapper](../scripts/reproduce.py) to build and run the sources in an ignored working directory.
- Use the [verification wrapper](../scripts/verify.py) to verify recorded evidence without running circuits.
- [Frozen analysis tools](frozen-tools/bounded_qip/) remain byte-identical to the original experiment freeze.
- [Older inherited tools](frozen-tools/windowed_pingpong/) are preserved for provenance. Their historical paths and commands are not the repository's current entry points.

See [reproduction instructions](../docs/REPRODUCTION.md) and [upstream attribution](UPSTREAM_NOTICE.txt). Source snapshots do not include large operation streams or native executables. They do include their Cargo lockfiles.
