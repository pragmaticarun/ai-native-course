//! In-process contract test: a real rmcp client talks to the server over a duplex pipe.
//! The ffmpeg-backed calls need `ffmpeg`/`ffprobe` on PATH (installed in CI).
use media_probe::MediaProbe;
use rmcp::{
    ClientHandler, ServiceExt,
    model::{CallToolRequestParams, ClientConfig},
};
use serde_json::{Value, json};

#[derive(Clone, Default)]
struct Client;
impl ClientHandler for Client {
    fn get_info(&self) -> ClientConfig {
        ClientConfig::default()
    }
}

fn args(v: Value) -> serde_json::Map<String, Value> {
    v.as_object().unwrap().clone()
}

#[tokio::test]
async fn tools_contract() -> anyhow::Result<()> {
    let dir = tempfile::tempdir()?;
    // 2 s of a 440 Hz sine at 48 kHz, generated with ffmpeg's lavfi source.
    let status = std::process::Command::new("ffmpeg")
        .args([
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
        ])
        .arg(dir.path().join("tone.wav"))
        .status()?;
    assert!(status.success());

    let (server_io, client_io) = tokio::io::duplex(1 << 16);
    let server = MediaProbe::new(dir.path());
    tokio::spawn(async move {
        server.serve(server_io).await?.waiting().await?;
        anyhow::Ok(())
    });
    let client = Client.serve(client_io).await?;

    let tools = client.list_all_tools().await?;
    let mut names: Vec<_> = tools.iter().map(|t| t.name.to_string()).collect();
    names.sort();
    assert_eq!(names, ["loudness", "probe"]);
    assert!(tools.iter().all(|t| t.output_schema.is_some()));

    let probe = client
        .call_tool(
            CallToolRequestParams::new("probe").with_arguments(args(json!({"path": "tone.wav"}))),
        )
        .await?;
    let s = probe.structured_content.expect("structured");
    assert!((s["duration_s"].as_f64().unwrap() - 2.0).abs() < 0.05);
    assert_eq!(s["streams"][0]["codec_type"], "audio");
    assert_eq!(s["streams"][0]["sample_rate"], 48000);

    let loud = client
        .call_tool(
            CallToolRequestParams::new("loudness")
                .with_arguments(args(json!({"path": "tone.wav"}))),
        )
        .await?;
    let l = loud.structured_content.expect("structured");
    assert!(l["integrated_lufs"].as_f64().unwrap() < 0.0);

    let bad = client
        .call_tool(
            CallToolRequestParams::new("probe").with_arguments(args(json!({"path": "../x"}))),
        )
        .await?;
    assert_eq!(bad.is_error, Some(true));
    client.cancel().await?;
    Ok(())
}
