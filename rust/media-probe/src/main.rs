//! stdio entry point: `media-probe <media-root>`. Logs go to stderr; stdout is the MCP channel.
use media_probe::MediaProbe;
use rmcp::{ServiceExt, transport::stdio};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let root = std::env::args().nth(1).unwrap_or_else(|| ".".into());
    let service = MediaProbe::new(root).serve(stdio()).await?;
    service.waiting().await?;
    Ok(())
}
