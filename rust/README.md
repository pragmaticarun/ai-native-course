# rust/

| Crate | Module | What |
|---|---|---|
| `media-probe/` | M9 (used by P3 later) | MCP server built with `rmcp` 3.10.0: `probe` (ffprobe summary) and `loudness` (ffmpeg `loudnorm`) as structured-output tools, path escapes refused, stdio transport |

```bash
cd media-probe
cargo test            # unit tests + an rmcp client/server test over an in-memory duplex (needs ffmpeg)
cargo build           # target/debug/media-probe <media-root>  (stdio MCP server)
```

The toolchain is pinned in `media-probe/rust-toolchain.toml` (1.100.0). The Python and TypeScript
contract tests in `examples/python/m9` and `examples/ts/m9` drive the built binary over stdio on both
MCP revisions (CI job `rust`). The P8 emulator screenshot/diff helper is still planned.
