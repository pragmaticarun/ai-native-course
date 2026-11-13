# rust/ — Rust components

Verify: `cargo fmt --check && cargo clippy --all-targets --locked -- -D warnings && cargo test --locked`

- Run it inside the crate directory (`rust/media-probe`). The toolchain is pinned in its `rust-toolchain.toml`.
- Clippy warnings fail CI. Keep `unsafe` out unless a spec asks for it.
- The Python and TypeScript MCP contract tests also drive the release binary: rebuild before running them.
